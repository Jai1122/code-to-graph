package main

import (
	"fmt"
	"go/ast"
	"go/token"

	"golang.org/x/tools/go/packages"
)

// SimpleCFGAnalyzer provides a basic CFG analysis without using golang.org/x/tools/go/cfg
// This avoids the panic issues and provides essential control flow information
type SimpleCFGAnalyzer struct {
	fileSet *token.FileSet
	verbose bool
}

// NewSimpleCFGAnalyzer creates a new simple CFG analyzer
func NewSimpleCFGAnalyzer(fset *token.FileSet, verbose bool) *SimpleCFGAnalyzer {
	return &SimpleCFGAnalyzer{
		fileSet: fset,
		verbose: verbose,
	}
}

// AnalyzeControlFlow performs basic control flow analysis
func (sca *SimpleCFGAnalyzer) AnalyzeControlFlow(pkgs []*packages.Package) ControlFlowAnalysis {
	var allCFGs []CFGResult
	
	for _, pkg := range pkgs {
		if len(pkg.Errors) > 0 {
			continue // Skip packages with errors
		}
		
		// Analyze each file in the package
		for _, file := range pkg.Syntax {
			cfgs := sca.analyzeFunctions(file, pkg)
			allCFGs = append(allCFGs, cfgs...)
		}
	}
	
	return ControlFlowAnalysis{
		Functions: allCFGs,
		Summary:   sca.calculateSummary(allCFGs),
	}
}

// analyzeFunctions extracts and analyzes all functions in a file
func (sca *SimpleCFGAnalyzer) analyzeFunctions(file *ast.File, pkg *packages.Package) []CFGResult {
	var results []CFGResult
	
	// Walk the AST to find function declarations
	ast.Inspect(file, func(n ast.Node) bool {
		switch node := n.(type) {
		case *ast.FuncDecl:
			if node.Body != nil { // Only analyze functions with bodies
				cfgResult := sca.buildSimpleCFG(node, pkg)
				results = append(results, cfgResult)
				
				if sca.verbose {
					fmt.Printf("Generated simple CFG for function %s: %d nodes, complexity %d\n", 
						cfgResult.FunctionName, len(cfgResult.Nodes), cfgResult.CyclomaticComplexity)
				}
			}
		}
		return true
	})
	
	return results
}

// buildSimpleCFG creates a basic control flow representation for a function
func (sca *SimpleCFGAnalyzer) buildSimpleCFG(fn *ast.FuncDecl, pkg *packages.Package) CFGResult {
	// Generate function ID
	functionID := fmt.Sprintf("func_%s_%d", fn.Name.Name, sca.fileSet.Position(fn.Pos()).Line)
	
	// Analyze the function body for control flow structures
	analyzer := &functionAnalyzer{
		fileSet: sca.fileSet,
		function: fn,
	}
	
	nodes := analyzer.analyzeBody(fn.Body)
	
	// Calculate basic cyclomatic complexity
	// Complexity = decision points + 1
	cyclomaticComplexity := analyzer.countDecisionPoints(fn.Body) + 1
	
	return CFGResult{
		FunctionName:         fn.Name.Name,
		FunctionID:           functionID,
		Nodes:                nodes,
		EdgeCount:            len(nodes) + analyzer.countBranches(fn.Body),
		CyclomaticComplexity: cyclomaticComplexity,
		UnreachableBlocks:    []int{}, // Basic implementation doesn't detect unreachable blocks
	}
}

// functionAnalyzer analyzes individual functions
type functionAnalyzer struct {
	fileSet  *token.FileSet
	function *ast.FuncDecl
	nodeID   int
}

// analyzeBody analyzes the function body and creates CFG nodes
func (fa *functionAnalyzer) analyzeBody(body *ast.BlockStmt) []CFGNode {
	var nodes []CFGNode
	
	if body == nil {
		return nodes
	}
	
	// Entry node
	entryNode := CFGNode{
		ID:          fa.nextNodeID(),
		Kind:        "entry",
		Statement:   fmt.Sprintf("Entry: %s", fa.function.Name.Name),
		Line:        fa.fileSet.Position(fa.function.Pos()).Line,
		Successors:  []int{},
		Predecessors: []int{},
	}
	
	if len(body.List) > 0 {
		entryNode.Successors = append(entryNode.Successors, entryNode.ID+1)
	}
	
	nodes = append(nodes, entryNode)
	
	// Analyze each statement
	for _, stmt := range body.List {
		stmtNodes := fa.analyzeStatement(stmt)
		nodes = append(nodes, stmtNodes...)
	}
	
	// Exit node if function has statements
	if len(body.List) > 0 {
		exitNode := CFGNode{
			ID:           fa.nextNodeID(),
			Kind:         "exit",
			Statement:    fmt.Sprintf("Exit: %s", fa.function.Name.Name),
			Line:         fa.fileSet.Position(body.End()).Line,
			Successors:   []int{},
			Predecessors: []int{fa.nodeID - 1}, // Previous node
		}
		nodes = append(nodes, exitNode)
		
		// Update last regular node to point to exit
		if len(nodes) > 1 {
			nodes[len(nodes)-2].Successors = append(nodes[len(nodes)-2].Successors, exitNode.ID)
		}
	}
	
	return nodes
}

// analyzeStatement creates CFG nodes for individual statements
func (fa *functionAnalyzer) analyzeStatement(stmt ast.Stmt) []CFGNode {
	var nodes []CFGNode
	
	switch s := stmt.(type) {
	case *ast.IfStmt:
		nodes = append(nodes, fa.analyzeIfStmt(s))
	case *ast.ForStmt:
		nodes = append(nodes, fa.analyzeForStmt(s))
	case *ast.RangeStmt:
		nodes = append(nodes, fa.analyzeRangeStmt(s))
	case *ast.SwitchStmt:
		nodes = append(nodes, fa.analyzeSwitchStmt(s))
	case *ast.ReturnStmt:
		nodes = append(nodes, fa.analyzeReturnStmt(s))
	case *ast.ExprStmt, *ast.AssignStmt, *ast.DeclStmt:
		nodes = append(nodes, fa.analyzeRegularStmt(s))
	default:
		nodes = append(nodes, fa.analyzeRegularStmt(s))
	}
	
	return nodes
}

// analyzeIfStmt creates nodes for if statements
func (fa *functionAnalyzer) analyzeIfStmt(stmt *ast.IfStmt) CFGNode {
	nodeID := fa.nextNodeID()
	
	condition := "if condition"
	if stmt.Cond != nil {
		condition = fmt.Sprintf("if %s", fa.nodeToString(stmt.Cond))
	}
	
	return CFGNode{
		ID:          nodeID,
		Kind:        "if",
		Statement:   condition,
		Line:        fa.fileSet.Position(stmt.Pos()).Line,
		Successors:  []int{nodeID + 1}, // Simplified: assume one successor
		Predecessors: []int{},
	}
}

// analyzeForStmt creates nodes for for loops
func (fa *functionAnalyzer) analyzeForStmt(stmt *ast.ForStmt) CFGNode {
	nodeID := fa.nextNodeID()
	
	return CFGNode{
		ID:          nodeID,
		Kind:        "for",
		Statement:   "for loop",
		Line:        fa.fileSet.Position(stmt.Pos()).Line,
		Successors:  []int{nodeID + 1},
		Predecessors: []int{},
	}
}

// analyzeRangeStmt creates nodes for range loops
func (fa *functionAnalyzer) analyzeRangeStmt(stmt *ast.RangeStmt) CFGNode {
	nodeID := fa.nextNodeID()
	
	return CFGNode{
		ID:          nodeID,
		Kind:        "range",
		Statement:   "range loop",
		Line:        fa.fileSet.Position(stmt.Pos()).Line,
		Successors:  []int{nodeID + 1},
		Predecessors: []int{},
	}
}

// analyzeSwitchStmt creates nodes for switch statements
func (fa *functionAnalyzer) analyzeSwitchStmt(stmt *ast.SwitchStmt) CFGNode {
	nodeID := fa.nextNodeID()
	
	return CFGNode{
		ID:          nodeID,
		Kind:        "switch",
		Statement:   "switch statement",
		Line:        fa.fileSet.Position(stmt.Pos()).Line,
		Successors:  []int{nodeID + 1},
		Predecessors: []int{},
	}
}

// analyzeReturnStmt creates nodes for return statements
func (fa *functionAnalyzer) analyzeReturnStmt(stmt *ast.ReturnStmt) CFGNode {
	nodeID := fa.nextNodeID()
	
	returnStmt := "return"
	if len(stmt.Results) > 0 {
		returnStmt = fmt.Sprintf("return %s", fa.nodeToString(stmt.Results[0]))
	}
	
	return CFGNode{
		ID:          nodeID,
		Kind:        "return",
		Statement:   returnStmt,
		Line:        fa.fileSet.Position(stmt.Pos()).Line,
		Successors:  []int{}, // Return statements have no successors
		Predecessors: []int{},
	}
}

// analyzeRegularStmt creates nodes for regular statements
func (fa *functionAnalyzer) analyzeRegularStmt(stmt ast.Stmt) CFGNode {
	nodeID := fa.nextNodeID()
	
	var stmtStr string
	var kind string
	
	switch s := stmt.(type) {
	case *ast.ExprStmt:
		kind = "expression"
		stmtStr = fa.nodeToString(s.X)
	case *ast.AssignStmt:
		kind = "assignment"
		if len(s.Lhs) > 0 && len(s.Rhs) > 0 {
			stmtStr = fmt.Sprintf("%s %s %s", fa.nodeToString(s.Lhs[0]), s.Tok.String(), fa.nodeToString(s.Rhs[0]))
		} else {
			stmtStr = "assignment"
		}
	case *ast.DeclStmt:
		kind = "declaration"
		stmtStr = "declaration"
	default:
		kind = "statement"
		stmtStr = fmt.Sprintf("%T", stmt)
	}
	
	return CFGNode{
		ID:          nodeID,
		Kind:        kind,
		Statement:   stmtStr,
		Line:        fa.fileSet.Position(stmt.Pos()).Line,
		Successors:  []int{nodeID + 1}, // Regular statements flow to next
		Predecessors: []int{},
	}
}

// countDecisionPoints counts decision points for cyclomatic complexity
func (fa *functionAnalyzer) countDecisionPoints(body *ast.BlockStmt) int {
	count := 0
	
	ast.Inspect(body, func(n ast.Node) bool {
		switch n.(type) {
		case *ast.IfStmt:
			count++
		case *ast.ForStmt:
			count++
		case *ast.RangeStmt:
			count++
		case *ast.SwitchStmt:
			count++
		case *ast.TypeSwitchStmt:
			count++
		case *ast.SelectStmt:
			count++
		}
		return true
	})
	
	return count
}

// countBranches counts branch points for edge calculation
func (fa *functionAnalyzer) countBranches(body *ast.BlockStmt) int {
	branches := 0
	
	ast.Inspect(body, func(n ast.Node) bool {
		switch n.(type) {
		case *ast.IfStmt:
			branches += 2 // if/else
		case *ast.ForStmt, *ast.RangeStmt:
			branches += 2 // enter/exit loop
		case *ast.SwitchStmt:
			branches += 2 // default case handling
		}
		return true
	})
	
	return branches
}

// nextNodeID generates the next unique node ID
func (fa *functionAnalyzer) nextNodeID() int {
	id := fa.nodeID
	fa.nodeID++
	return id
}

// nodeToString converts an AST node to a string representation
func (fa *functionAnalyzer) nodeToString(node ast.Node) string {
	switch n := node.(type) {
	case *ast.Ident:
		return n.Name
	case *ast.BasicLit:
		return n.Value
	case *ast.BinaryExpr:
		return fmt.Sprintf("%s %s %s", fa.nodeToString(n.X), n.Op.String(), fa.nodeToString(n.Y))
	case *ast.UnaryExpr:
		return fmt.Sprintf("%s%s", n.Op.String(), fa.nodeToString(n.X))
	case *ast.CallExpr:
		return fmt.Sprintf("%s()", fa.nodeToString(n.Fun))
	case *ast.SelectorExpr:
		return fmt.Sprintf("%s.%s", fa.nodeToString(n.X), n.Sel.Name)
	default:
		pos := fa.fileSet.Position(node.Pos())
		return fmt.Sprintf("<%T>@%d", node, pos.Line)
	}
}

// calculateSummary computes summary statistics for all CFG results
func (sca *SimpleCFGAnalyzer) calculateSummary(cfgs []CFGResult) struct {
	TotalFunctions      int     `json:"total_functions"`
	AverageComplexity   float64 `json:"average_complexity"`
	MaxComplexity       int     `json:"max_complexity"`
	TotalUnreachable    int     `json:"total_unreachable_blocks"`
} {
	summary := struct {
		TotalFunctions      int     `json:"total_functions"`
		AverageComplexity   float64 `json:"average_complexity"`
		MaxComplexity       int     `json:"max_complexity"`
		TotalUnreachable    int     `json:"total_unreachable_blocks"`
	}{
		TotalFunctions: len(cfgs),
	}
	
	if len(cfgs) == 0 {
		return summary
	}
	
	totalComplexity := 0
	maxComplexity := 0
	totalUnreachable := 0
	
	for _, cfg := range cfgs {
		totalComplexity += cfg.CyclomaticComplexity
		if cfg.CyclomaticComplexity > maxComplexity {
			maxComplexity = cfg.CyclomaticComplexity
		}
		totalUnreachable += len(cfg.UnreachableBlocks)
	}
	
	summary.AverageComplexity = float64(totalComplexity) / float64(len(cfgs))
	summary.MaxComplexity = maxComplexity
	summary.TotalUnreachable = totalUnreachable
	
	return summary
}
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"go/ast"
	"go/token"
	"go/types"
	"log"
	"os"
	"path/filepath"
	"strings"

	"golang.org/x/tools/go/packages"
)

// Entity represents a code entity (function, type, method, etc.)
type Entity struct {
	ID           string            `json:"id"`
	Name         string            `json:"name"`
	Type         string            `json:"type"`
	Package      string            `json:"package"`
	File         string            `json:"file"`
	StartLine    int               `json:"start_line"`
	EndLine      int               `json:"end_line"`
	Signature    string            `json:"signature,omitempty"`
	ReceiverType string            `json:"receiver_type,omitempty"`
	ReturnType   string            `json:"return_type,omitempty"`
	Interfaces   []string          `json:"interfaces,omitempty"`
	Fields       []string          `json:"fields,omitempty"`
	Methods      []string          `json:"methods,omitempty"`
	Code         string            `json:"code,omitempty"`
	DocString    string            `json:"doc_string,omitempty"`
	Metadata     map[string]string `json:"metadata,omitempty"`
}

// Relationship represents a relationship between entities
type Relationship struct {
	ID         string            `json:"id"`
	SourceID   string            `json:"source_id"`
	SourceName string            `json:"source_name"`
	TargetID   string            `json:"target_id"`
	TargetName string            `json:"target_name"`
	Type       string            `json:"type"`
	Line       int               `json:"line,omitempty"`
	Metadata   map[string]string `json:"metadata,omitempty"`
}

// CFGNode represents a node in the control flow graph
type CFGNode struct {
	ID          int      `json:"id"`
	Kind        string   `json:"kind"`
	Statement   string   `json:"statement,omitempty"`
	Line        int      `json:"line"`
	Successors  []int    `json:"successors"`
	Predecessors []int   `json:"predecessors"`
}

// CFGResult represents the control flow graph for a function
type CFGResult struct {
	FunctionName        string    `json:"function_name"`
	FunctionID          string    `json:"function_id"`
	Nodes               []CFGNode `json:"nodes"`
	EdgeCount           int       `json:"edge_count"`
	CyclomaticComplexity int      `json:"cyclomatic_complexity"`
	UnreachableBlocks   []int     `json:"unreachable_blocks"`
}

// ControlFlowAnalysis contains all CFG results
type ControlFlowAnalysis struct {
	Functions []CFGResult `json:"functions"`
	Summary   struct {
		TotalFunctions      int     `json:"total_functions"`
		AverageComplexity   float64 `json:"average_complexity"`
		MaxComplexity       int     `json:"max_complexity"`
		TotalUnreachable    int     `json:"total_unreachable_blocks"`
	} `json:"summary"`
}

// DeepAnalysisFlags controls which deep analysis features to enable
type DeepAnalysisFlags struct {
	EnableCFG bool
}

// DeepAnalysis contains advanced static analysis results
type DeepAnalysis struct {
	ControlFlow *ControlFlowAnalysis `json:"control_flow,omitempty"`
}

// AnalysisResult contains the complete analysis
type AnalysisResult struct {
	Success       bool           `json:"success"`
	Error         string         `json:"error,omitempty"`
	Language      string         `json:"language"`
	Entities      []Entity       `json:"entities"`
	Relationships []Relationship `json:"relationships"`
	DeepAnalysis  *DeepAnalysis  `json:"deep_analysis,omitempty"`
	Stats         AnalysisStats  `json:"stats"`
}

// AnalysisStats contains analysis statistics
type AnalysisStats struct {
	TotalFiles         int            `json:"total_files"`
	TotalPackages      int            `json:"total_packages"`
	TotalEntities      int            `json:"total_entities"`
	TotalRelationships int            `json:"total_relationships"`
	EntitiesByType     map[string]int `json:"entities_by_type"`
	RelationshipsByType map[string]int `json:"relationships_by_type"`
}

func main() {
	var (
		repoPath         = flag.String("repo-path", ".", "Path to Go repository")
		outputFile       = flag.String("output", "", "Output file path (default: stdout)")
		includeCode      = flag.Bool("include-code", false, "Include source code in entities")
		verbose          = flag.Bool("verbose", false, "Enable verbose logging")
		pattern          = flag.String("pattern", "./...", "Go package pattern to analyze")
		enableCFG        = flag.Bool("enable-cfg", false, "Enable Control Flow Graph analysis")
		enableDeepAnalysis = flag.Bool("enable-deep-analysis", false, "Enable all deep analysis features")
	)
	flag.Parse()

	if *verbose {
		log.SetOutput(os.Stderr)
	} else {
		log.SetOutput(os.Stderr)
		log.SetFlags(0)
	}

	// Set deep analysis flags
	deepFlags := DeepAnalysisFlags{
		EnableCFG: *enableCFG || *enableDeepAnalysis,
	}
	
	result := analyzeGoRepository(*repoPath, *pattern, *includeCode, *verbose, deepFlags)

	var output *os.File
	var err error
	if *outputFile != "" {
		output, err = os.Create(*outputFile)
		if err != nil {
			log.Fatalf("Failed to create output file: %v", err)
		}
		defer output.Close()
	} else {
		output = os.Stdout
	}

	encoder := json.NewEncoder(output)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(result); err != nil {
		log.Fatalf("Failed to encode JSON: %v", err)
	}
}

func analyzeGoRepository(repoPath, pattern string, includeCode, verbose bool, deepFlags DeepAnalysisFlags) AnalysisResult {
	if verbose {
		log.Printf("Analyzing Go repository at: %s with pattern: %s", repoPath, pattern)
	}

	// Change to repository directory
	if err := os.Chdir(repoPath); err != nil {
		return AnalysisResult{
			Success:  false,
			Error:    fmt.Sprintf("Failed to change directory to %s: %v", repoPath, err),
			Language: "go",
		}
	}

	// Configure package loading
	cfg := &packages.Config{
		Mode: packages.NeedName | packages.NeedFiles |
			packages.NeedImports | packages.NeedTypes |
			packages.NeedTypesInfo | packages.NeedSyntax,
		Dir:        ".",
		BuildFlags: []string{"-tags=ignore_build_constraints"},
		Env:        append(os.Environ(), "GO111MODULE=off"), // For single files
	}

	// Load packages
	pkgs, err := packages.Load(cfg, pattern)
	if err != nil {
		return AnalysisResult{
			Success:  false,
			Error:    fmt.Sprintf("Failed to load packages: %v", err),
			Language: "go",
		}
	}

	if verbose {
		log.Printf("Loaded %d packages", len(pkgs))
	}

	// Check for package errors
	var packageErrors []string
	for _, pkg := range pkgs {
		if len(pkg.Errors) > 0 {
			for _, err := range pkg.Errors {
				packageErrors = append(packageErrors, fmt.Sprintf("Package %s: %v", pkg.Name, err))
			}
		}
	}

	var entities []Entity
	var relationships []Relationship
	entityCounter := 0
	relationshipCounter := 0
	var fset *token.FileSet

	// Analyze each package
	for _, pkg := range pkgs {
		if len(pkg.Errors) > 0 {
			continue // Skip packages with errors
		}

		if verbose {
			log.Printf("Analyzing package: %s (%d files)", pkg.Name, len(pkg.Syntax))
		}

		// Analyze each file in the package
		for _, file := range pkg.Syntax {
			fset = pkg.Fset
			filename := fset.Position(file.Pos()).Filename
			
			// Make filename relative to repo root
			if relPath, err := filepath.Rel(repoPath, filename); err == nil {
				filename = relPath
			}

			// Extract entities from this file
			fileEntities, fileRelationships := extractEntitiesFromFile(
				file, pkg, fset, filename, includeCode, &entityCounter, &relationshipCounter)
			
			entities = append(entities, fileEntities...)
			relationships = append(relationships, fileRelationships...)
		}

		// Extract interface implementations
		interfaceRels := extractInterfaceImplementations(pkg, &relationshipCounter)
		relationships = append(relationships, interfaceRels...)
	}

	// Perform deep analysis if enabled
	var deepAnalysis *DeepAnalysis
	if deepFlags.EnableCFG {
		if verbose {
			log.Printf("Performing deep analysis...")
		}
		
		deepAnalysis = &DeepAnalysis{}
		
		// Control Flow Graph analysis (using simple implementation to avoid crashes)
		cfgAnalyzer := NewSimpleCFGAnalyzer(fset, verbose)
		cfgResults := cfgAnalyzer.AnalyzeControlFlow(pkgs)
		deepAnalysis.ControlFlow = &cfgResults
		
		if verbose {
			log.Printf("CFG analysis completed: %d functions analyzed, average complexity %.2f", 
				cfgResults.Summary.TotalFunctions, cfgResults.Summary.AverageComplexity)
		}
	}

	// Calculate statistics
	stats := calculateStats(entities, relationships, pkgs)

	result := AnalysisResult{
		Success:       true,
		Language:      "go",
		Entities:      entities,
		Relationships: relationships,
		DeepAnalysis:  deepAnalysis,
		Stats:         stats,
	}

	// Add package errors as metadata if any
	if len(packageErrors) > 0 {
		result.Error = fmt.Sprintf("Package errors: %s", strings.Join(packageErrors, "; "))
	}

	if verbose {
		log.Printf("Analysis complete: %d entities, %d relationships", len(entities), len(relationships))
	}

	return result
}

func extractEntitiesFromFile(file *ast.File, pkg *packages.Package, fset *token.FileSet, 
	filename string, includeCode bool, entityCounter, relationshipCounter *int) ([]Entity, []Relationship) {
	
	var entities []Entity
	var relationships []Relationship

	// Walk the AST
	ast.Inspect(file, func(n ast.Node) bool {
		switch node := n.(type) {
		case *ast.FuncDecl:
			entity := analyzeFuncDecl(node, pkg, fset, filename, includeCode, entityCounter)
			entities = append(entities, entity)
			
			// Extract function calls from this function
			rels := extractFunctionCalls(node, entity.ID, pkg, fset, relationshipCounter)
			relationships = append(relationships, rels...)
			
		case *ast.GenDecl:
			if node.Tok == token.TYPE {
				for _, spec := range node.Specs {
					if typeSpec, ok := spec.(*ast.TypeSpec); ok {
						entity := analyzeTypeDecl(typeSpec, pkg, fset, filename, includeCode, entityCounter)
						entities = append(entities, entity)
					}
				}
			} else if node.Tok == token.VAR || node.Tok == token.CONST {
				for _, spec := range node.Specs {
					if valueSpec, ok := spec.(*ast.ValueSpec); ok {
						for _, name := range valueSpec.Names {
							entity := analyzeValueDecl(name, valueSpec, node.Tok, pkg, fset, filename, includeCode, entityCounter)
							entities = append(entities, entity)
						}
					}
				}
			}
		}
		return true
	})

	return entities, relationships
}

func analyzeFuncDecl(fn *ast.FuncDecl, pkg *packages.Package, fset *token.FileSet, 
	filename string, includeCode bool, counter *int) Entity {
	
	*counter++
	startPos := fset.Position(fn.Pos())
	endPos := fset.Position(fn.End())
	
	entity := Entity{
		ID:       fmt.Sprintf("func_%d", *counter),
		Name:     fn.Name.Name,
		Type:     "function",
		Package:  pkg.Name,
		File:     filename,
		StartLine: startPos.Line,
		EndLine:   endPos.Line,
		Metadata:  make(map[string]string),
	}

	// Check if it's a method (has receiver)
	if fn.Recv != nil && len(fn.Recv.List) > 0 {
		entity.Type = "method"
		if pkg.TypesInfo != nil {
			if t := pkg.TypesInfo.TypeOf(fn.Recv.List[0].Type); t != nil {
				entity.ReceiverType = t.String()
				entity.Metadata["receiver_type"] = entity.ReceiverType
			}
		}
	}

	// Get function signature and return type
	if pkg.TypesInfo != nil {
		if obj := pkg.TypesInfo.ObjectOf(fn.Name); obj != nil {
			entity.Signature = obj.Type().String()
			
			// Extract return type for functions
			if sig, ok := obj.Type().(*types.Signature); ok {
				if sig.Results() != nil && sig.Results().Len() > 0 {
					entity.ReturnType = sig.Results().At(0).Type().String()
				}
				
				// Add parameter information
				if sig.Params() != nil && sig.Params().Len() > 0 {
					var params []string
					for i := 0; i < sig.Params().Len(); i++ {
						param := sig.Params().At(i)
						params = append(params, param.Type().String())
					}
					entity.Metadata["parameters"] = strings.Join(params, ",")
				}
			}
		}
	}

	// Extract documentation
	if fn.Doc != nil {
		entity.DocString = fn.Doc.Text()
	}

	// Include source code if requested
	if includeCode {
		// This would require reading the source file, simplified for now
		entity.Code = fmt.Sprintf("// Function %s at line %d", fn.Name.Name, startPos.Line)
	}

	// Add metadata
	entity.Metadata["visibility"] = getVisibility(fn.Name.Name)
	if fn.Recv != nil {
		entity.Metadata["is_method"] = "true"
	} else {
		entity.Metadata["is_method"] = "false"
	}

	return entity
}

func analyzeTypeDecl(typeSpec *ast.TypeSpec, pkg *packages.Package, fset *token.FileSet, 
	filename string, includeCode bool, counter *int) Entity {
	
	*counter++
	startPos := fset.Position(typeSpec.Pos())
	endPos := fset.Position(typeSpec.End())
	
	entity := Entity{
		ID:       fmt.Sprintf("type_%d", *counter),
		Name:     typeSpec.Name.Name,
		Type:     "type",
		Package:  pkg.Name,
		File:     filename,
		StartLine: startPos.Line,
		EndLine:   endPos.Line,
		Metadata:  make(map[string]string),
	}

	// Analyze different type kinds
	switch t := typeSpec.Type.(type) {
	case *ast.StructType:
		entity.Type = "struct"
		entity.Metadata["kind"] = "struct"
		
		// Extract field names and types
		if t.Fields != nil {
			for _, field := range t.Fields.List {
				if field.Names != nil {
					for _, name := range field.Names {
						entity.Fields = append(entity.Fields, name.Name)
						
						// Add field type information
						if pkg.TypesInfo != nil {
							if fieldType := pkg.TypesInfo.TypeOf(field.Type); fieldType != nil {
								entity.Metadata[fmt.Sprintf("field_%s_type", name.Name)] = fieldType.String()
							}
						}
					}
				} else {
					// Embedded field
					if pkg.TypesInfo != nil {
						if fieldType := pkg.TypesInfo.TypeOf(field.Type); fieldType != nil {
							entity.Fields = append(entity.Fields, fmt.Sprintf("embedded_%s", fieldType.String()))
							entity.Metadata["has_embedded_fields"] = "true"
						}
					}
				}
			}
		}
		
	case *ast.InterfaceType:
		entity.Type = "interface"
		entity.Metadata["kind"] = "interface"
		
		// Extract method signatures
		if t.Methods != nil {
			for _, method := range t.Methods.List {
				if method.Names != nil {
					for _, name := range method.Names {
						entity.Methods = append(entity.Methods, name.Name)
						
						// Add method signature
						if pkg.TypesInfo != nil {
							if methodType := pkg.TypesInfo.TypeOf(method.Type); methodType != nil {
								entity.Metadata[fmt.Sprintf("method_%s_signature", name.Name)] = methodType.String()
							}
						}
					}
				}
			}
		}
		
	default:
		entity.Metadata["kind"] = "alias"
		if pkg.TypesInfo != nil {
			if underlyingType := pkg.TypesInfo.TypeOf(typeSpec.Type); underlyingType != nil {
				entity.Metadata["underlying_type"] = underlyingType.String()
			}
		}
	}

	// Add visibility metadata
	entity.Metadata["visibility"] = getVisibility(typeSpec.Name.Name)

	return entity
}

func analyzeValueDecl(name *ast.Ident, spec *ast.ValueSpec, tok token.Token, pkg *packages.Package, 
	fset *token.FileSet, filename string, includeCode bool, counter *int) Entity {
	
	*counter++
	startPos := fset.Position(name.Pos())
	
	entityType := "variable"
	if tok == token.CONST {
		entityType = "constant"
	}
	
	entity := Entity{
		ID:       fmt.Sprintf("%s_%d", entityType, *counter),
		Name:     name.Name,
		Type:     entityType,
		Package:  pkg.Name,
		File:     filename,
		StartLine: startPos.Line,
		EndLine:   startPos.Line,
		Metadata:  make(map[string]string),
	}

	// Get type information
	if pkg.TypesInfo != nil {
		if obj := pkg.TypesInfo.ObjectOf(name); obj != nil {
			entity.Metadata["value_type"] = obj.Type().String()
		}
	}

	// Add visibility metadata
	entity.Metadata["visibility"] = getVisibility(name.Name)

	return entity
}

func extractFunctionCalls(fn *ast.FuncDecl, sourceID string, pkg *packages.Package, 
	fset *token.FileSet, counter *int) []Relationship {
	
	var relationships []Relationship
	
	ast.Inspect(fn, func(n ast.Node) bool {
		if call, ok := n.(*ast.CallExpr); ok {
			*counter++
			
			var targetName string
			var relationshipType = "calls"
			
			// Extract function name from call expression
			switch fun := call.Fun.(type) {
			case *ast.Ident:
				targetName = fun.Name
			case *ast.SelectorExpr:
				if ident, ok := fun.X.(*ast.Ident); ok {
					targetName = fmt.Sprintf("%s.%s", ident.Name, fun.Sel.Name)
					relationshipType = "method_call"
				} else {
					targetName = fun.Sel.Name
					relationshipType = "method_call"
				}
			default:
				targetName = "unknown"
			}
			
			relationship := Relationship{
				ID:         fmt.Sprintf("rel_%d", *counter),
				SourceID:   sourceID,
				SourceName: fn.Name.Name,
				TargetID:   "", // Will be resolved later if target is in same package
				TargetName: targetName,
				Type:       relationshipType,
				Line:       fset.Position(call.Pos()).Line,
				Metadata:   make(map[string]string),
			}
			
			// Add call type information
			if pkg.TypesInfo != nil {
				if callType := pkg.TypesInfo.TypeOf(call); callType != nil {
					relationship.Metadata["return_type"] = callType.String()
				}
			}
			
			relationships = append(relationships, relationship)
		}
		return true
	})
	
	return relationships
}

func extractInterfaceImplementations(pkg *packages.Package, counter *int) []Relationship {
	var relationships []Relationship
	
	// This is a simplified implementation - in practice, you'd do more comprehensive analysis
	for _, obj := range pkg.TypesInfo.Defs {
		if obj != nil && obj.Type() != nil {
			// Check if this type implements any interfaces
			// This would require more sophisticated analysis to be complete
			if named, ok := obj.Type().(*types.Named); ok {
				for i := 0; i < named.NumMethods(); i++ {
					method := named.Method(i)
					// Create method relationship
					*counter++
					relationship := Relationship{
						ID:         fmt.Sprintf("rel_%d", *counter),
						SourceID:   "", // Would need to resolve
						SourceName: obj.Name(),
						TargetID:   "",
						TargetName: method.Name(),
						Type:       "defines_method",
						Metadata:   map[string]string{
							"analysis_type": "method_definition",
							"method_signature": method.Type().String(),
						},
					}
					relationships = append(relationships, relationship)
				}
			}
		}
	}
	
	return relationships
}

func calculateStats(entities []Entity, relationships []Relationship, pkgs []*packages.Package) AnalysisStats {
	stats := AnalysisStats{
		TotalEntities:      len(entities),
		TotalRelationships: len(relationships),
		TotalPackages:      len(pkgs),
		EntitiesByType:     make(map[string]int),
		RelationshipsByType: make(map[string]int),
	}
	
	// Count files
	fileSet := make(map[string]bool)
	for _, entity := range entities {
		fileSet[entity.File] = true
	}
	stats.TotalFiles = len(fileSet)
	
	// Count entities by type
	for _, entity := range entities {
		stats.EntitiesByType[entity.Type]++
	}
	
	// Count relationships by type
	for _, rel := range relationships {
		stats.RelationshipsByType[rel.Type]++
	}
	
	return stats
}

func getVisibility(name string) string {
	if len(name) > 0 && name[0] >= 'A' && name[0] <= 'Z' {
		return "public"
	}
	return "private"
}
# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in CodeToGraph, please report it responsibly:

1. **Do NOT** open a public issue
2. Email the security team directly (replace with your actual contact)
3. Include as much detail as possible about the vulnerability
4. Allow reasonable time for the issue to be addressed before public disclosure

## Security Considerations

### Environment Variables and Secrets

CodeToGraph uses environment variables to manage sensitive configuration:

- **API Keys**: Never commit `.env` files containing real API keys
- **Database Passwords**: Use strong passwords for Neo4j
- **VPN Access**: Ensure proper VPN configuration for VLLM endpoints

### Recommended Security Practices

#### 1. Environment Configuration

```bash
# Use strong, unique passwords
NEO4J_PASSWORD=your-strong-password-here

# Use secure API keys
LLM_VLLM_API_KEY=your-secure-api-key

# Keep credentials in environment, not code
```

#### 2. Network Security

- Run Neo4j behind a firewall in production
- Use HTTPS for all VLLM endpoints
- Ensure VPN connections are properly configured
- Limit network access to required ports only

#### 3. Data Protection

- Avoid analyzing repositories containing sensitive data without review
- Consider data retention policies for analysis results
- Regularly clean temporary files and caches

#### 4. Dependency Security

- Keep dependencies updated regularly
- Monitor for security advisories
- Use `pip audit` to check for known vulnerabilities

```bash
pip install pip-audit
pip-audit
```

### Files That Should Never Be Committed

The `.gitignore` file prevents these from being committed:

- `.env` files with actual secrets
- API keys and credentials
- Database dumps
- Log files containing sensitive information
- Analysis results that might contain proprietary code

### Production Deployment

For production deployments:

1. Use environment-specific configuration files
2. Implement proper access controls
3. Enable audit logging
4. Use container security scanning
5. Implement network segmentation
6. Regular security updates

### Development Guidelines

- Use `.env.template` as a starting point
- Never hardcode secrets in source code
- Use secure development practices
- Review code for potential security issues
- Test with minimal required permissions

## Supported Versions

We provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Security Tools Integration

Consider integrating these security tools:

- **Bandit**: Python security linter
- **Safety**: Python dependency vulnerability scanner
- **Docker security scanning**: For container deployments
- **SAST tools**: Static application security testing

```bash
# Install security tools
pip install bandit safety

# Run security checks
bandit -r src/
safety check
```

## Contact

For security-related questions or to report vulnerabilities:

- Security Email: [Replace with actual contact]
- Response Time: 48-72 hours for initial response
- Disclosure Timeline: Coordinated disclosure within 90 days
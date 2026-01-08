## Pull Request Checklist

### Description
<!-- Provide a clear and concise description of the changes in this PR -->

**Related Issue:** <!-- Link to the issue this PR addresses (e.g., #123) -->

**Type of Change:**
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Infrastructure/DevOps (CI/CD, deployment, configuration)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring
- [ ] Security fix

### Testing Requirements

#### Backend Testing
- [ ] All existing tests pass (`pytest tests/ -v`)
- [ ] New tests added for new functionality (minimum 90% coverage)
- [ ] Integration tests updated if applicable
- [ ] Database migrations tested (up and down)
- [ ] API endpoints tested with various input scenarios
- [ ] Error handling and edge cases covered
- [ ] Performance impact assessed

#### Frontend Testing
- [ ] All existing tests pass (`npm run test`)
- [ ] New tests added for new components/features
- [ ] Type checking passes (`npm run type-check`)
- [ ] Component rendering tested across breakpoints
- [ ] User interactions tested
- [ ] Accessibility tested (keyboard navigation, screen readers)
- [ ] Browser compatibility verified

#### Manual Testing
- [ ] Tested locally with Docker Compose
- [ ] Tested in development environment
- [ ] Verified with production-like data
- [ ] Cross-browser testing completed (Chrome, Firefox, Safari, Edge)
- [ ] Mobile responsiveness verified
- [ ] Performance profiling completed

### Code Quality

#### Linting & Formatting
- [ ] Backend: `flake8` passes with no warnings
- [ ] Frontend: `npm run lint` passes with no errors
- [ ] Frontend: `npm run format:check` passes
- [ ] Code follows project naming conventions
- [ ] No commented-out code or debug statements
- [ ] Imports are organized and unused imports removed

#### Code Review Standards
- [ ] Code is self-documenting with clear variable/function names
- [ ] Complex logic includes explanatory comments
- [ ] Functions are focused and follow single responsibility principle
- [ ] No code duplication (DRY principle applied)
- [ ] Error messages are clear and actionable
- [ ] Logging includes appropriate context and correlation IDs

### Security Considerations

#### Security Checklist
- [ ] No hardcoded secrets, API keys, or credentials
- [ ] All user inputs are validated and sanitized
- [ ] SQL injection prevention (parameterized queries used)
- [ ] XSS prevention measures implemented
- [ ] CSRF protection in place for state-changing operations
- [ ] Authentication and authorization properly implemented
- [ ] Sensitive data is encrypted at rest and in transit
- [ ] Dependencies scanned for vulnerabilities (`npm audit`, `pip-audit`)
- [ ] No exposure of sensitive information in logs or error messages

#### Security Scanning
- [ ] CodeQL security analysis passed
- [ ] Dependency audit completed with no critical vulnerabilities
- [ ] SAST tools run successfully
- [ ] Security best practices followed per OWASP guidelines

### Documentation

#### Code Documentation
- [ ] Docstrings added for all new functions/classes (Python)
- [ ] JSDoc comments added for complex functions (TypeScript)
- [ ] Inline comments explain "why" not "what"
- [ ] Type hints provided (Python) / TypeScript types defined

#### Project Documentation
- [ ] README.md updated if setup/usage changed
- [ ] API documentation updated (if applicable)
- [ ] Architecture diagrams updated (if applicable)
- [ ] Migration guide provided for breaking changes
- [ ] Environment variables documented in `.env.example`

### Database Changes

- [ ] Database migrations created and tested
- [ ] Migration is reversible (down migration works)
- [ ] Migration tested with production-like data volume
- [ ] Indexes added for new query patterns
- [ ] No breaking changes to existing data structures
- [ ] Data migration strategy documented for production

### Deployment Readiness

#### CI/CD Pipeline
- [ ] All CI checks pass (tests, linting, security scans)
- [ ] Docker images build successfully
- [ ] No new warnings or errors in build logs
- [ ] Build time is reasonable (no significant increase)

#### Configuration
- [ ] Environment variables documented
- [ ] Configuration changes backward compatible
- [ ] Feature flags used for risky changes (if applicable)
- [ ] Secrets properly managed (not in code)

#### Deployment Strategy
- [ ] Deployment plan documented for complex changes
- [ ] Rollback procedure identified and tested
- [ ] Database migration strategy defined
- [ ] Zero-downtime deployment verified (if applicable)
- [ ] Health checks updated to verify new functionality

#### Monitoring & Observability
- [ ] Appropriate logging added with structured context
- [ ] Metrics/instrumentation added for key operations
- [ ] Error tracking configured for new features
- [ ] Performance monitoring in place
- [ ] Alerts configured for critical failures

### Performance

- [ ] No N+1 query problems introduced
- [ ] Database queries optimized with appropriate indexes
- [ ] Caching strategy implemented where beneficial
- [ ] Large data sets handled efficiently
- [ ] Memory usage is reasonable
- [ ] API response times meet SLA requirements
- [ ] Frontend bundle size impact assessed

### Accessibility

- [ ] Semantic HTML used
- [ ] ARIA labels provided where needed
- [ ] Keyboard navigation works correctly
- [ ] Color contrast meets WCAG AA standards
- [ ] Screen reader tested
- [ ] Focus management implemented properly

### Breaking Changes

<!-- If this PR includes breaking changes, describe them here -->

**Migration Path:**
<!-- Describe how users/systems should migrate to the new version -->

**Deprecation Warnings:**
<!-- List any deprecation warnings added -->

### Additional Notes

<!-- Any additional information that reviewers should know -->

### Screenshots/Videos

<!-- If applicable, add screenshots or videos demonstrating the changes -->

---

### Reviewer Guidelines

**For Reviewers:**
- [ ] Code follows project architecture and patterns
- [ ] Security considerations are adequate
- [ ] Test coverage is sufficient
- [ ] Documentation is clear and complete
- [ ] Performance impact is acceptable
- [ ] No obvious bugs or edge cases missed
- [ ] Code is maintainable and readable

**Approval Criteria:**
- All required checks must pass
- At least one approval from a code owner
- No unresolved conversations
- All CI/CD pipeline stages successful
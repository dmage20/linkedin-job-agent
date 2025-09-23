# Agent Orchestration System

## Overview

This document defines the automated handoff system between Agile team agents, enabling autonomous team coordination from a single user input to working software delivery.

## Orchestration Chain

```
User Input → Product Owner → Scrum Master → Technical Lead → Developer → QA/Tester → DevOps → Sprint Review → [Loop or Complete]
```

## Agent Handoff Specifications

### 1. Product Owner → Scrum Master

**Product Owner Completion Criteria**:
- [ ] Feature broken into user stories (3-8 stories typical)
- [ ] Each story has clear acceptance criteria (3-5 criteria each)
- [ ] Stories prioritized by business value (High/Medium/Low)
- [ ] Epic description with business context completed
- [ ] Dependencies between stories identified

**Auto-Trigger Condition**: When all completion criteria met

**Handoff Payload**:
```json
{
  "epic": {
    "title": "Feature name",
    "description": "Business context and value",
    "businessValue": "Why this matters"
  },
  "userStories": [
    {
      "id": "US-001",
      "title": "Story title",
      "description": "As a [user] I want [functionality] so that [value]",
      "acceptanceCriteria": ["criteria1", "criteria2", "criteria3"],
      "priority": "High|Medium|Low",
      "businessValue": "Impact description",
      "dependencies": ["US-002"]
    }
  ],
  "overallGoal": "Sprint objective",
  "stakeholderContext": "User's original request"
}
```

**Task Command**:
```
Use the Task tool to launch the Scrum Master with the above payload to plan sprint execution and estimate team capacity.
```

### 2. Scrum Master → Technical Lead

**Scrum Master Completion Criteria**:
- [ ] Sprint goal defined and aligned with user stories
- [ ] Story point estimates completed (1,2,3,5,8,13 scale)
- [ ] Sprint timeline planned (typically 2-5 days per increment)
- [ ] Team capacity assessed and realistic commitment made
- [ ] Risk assessment completed with mitigation strategies

**Auto-Trigger Condition**: When sprint planning complete and feasible

**Handoff Payload**:
```json
{
  "sprintPlan": {
    "goal": "Sprint objective",
    "duration": "2-5 days",
    "capacity": "Available story points",
    "commitment": "Committed stories"
  },
  "estimatedStories": [
    {
      "storyId": "US-001",
      "storyPoints": 5,
      "complexity": "Medium",
      "risks": ["Technical complexity", "Integration challenges"],
      "dependencies": ["US-002"]
    }
  ],
  "timeline": {
    "startDate": "Date",
    "endDate": "Date",
    "milestones": ["Milestone1", "Milestone2"]
  },
  "previousContext": "All Product Owner output"
}
```

**Task Command**:
```
Use the Task tool to launch the Technical Lead with sprint plan and story details to provide architectural guidance and technical implementation approach.
```

### 3. Technical Lead → Developer

**Technical Lead Completion Criteria**:
- [ ] Architecture approach defined for each story
- [ ] Technical dependencies and integration points identified
- [ ] Coding standards and patterns specified
- [ ] Database/API design decisions made
- [ ] Testing strategy outlined (unit, integration, e2e)
- [ ] Performance and security considerations documented

**Auto-Trigger Condition**: When technical approach is complete and implementable

**Handoff Payload**:
```json
{
  "technicalGuidance": {
    "architecture": "Overall approach and patterns",
    "technologies": ["Required tech stack"],
    "databaseDesign": "Schema and model decisions",
    "apiDesign": "Endpoint and interface specifications",
    "securityApproach": "Authentication, authorization, data protection"
  },
  "implementationPlan": [
    {
      "storyId": "US-001",
      "technicalApproach": "Specific implementation strategy",
      "testingStrategy": "Unit, integration, e2e test requirements",
      "codeStructure": "Files to create/modify",
      "dependencies": "External libraries or services needed"
    }
  ],
  "qualityStandards": {
    "testCoverage": "95%+",
    "codeReview": "Required",
    "performanceTargets": "Response time < 200ms"
  },
  "previousContext": "All Product Owner and Scrum Master output"
}
```

**Task Command**:
```
Use the Task tool to launch the Developer with complete technical guidance to implement features using Test-Driven Development approach.
```

### 4. Developer → QA/Tester

**Developer Completion Criteria**:
- [ ] All user stories implemented with passing tests
- [ ] TDD cycle completed (Red-Green-Refactor) for each feature
- [ ] Unit test coverage ≥95%
- [ ] Integration points working and tested
- [ ] Code follows technical lead's guidance and standards
- [ ] Self-code review completed
- [ ] Working software ready for validation

**Auto-Trigger Condition**: When implementation complete with all tests passing

**Handoff Payload**:
```json
{
  "implementation": {
    "completedStories": ["US-001", "US-002"],
    "codeChanges": "Summary of files created/modified",
    "testCoverage": "96%",
    "performanceMetrics": "Response times, memory usage"
  },
  "testResults": {
    "unitTests": "45 tests, 45 passing",
    "integrationTests": "12 tests, 12 passing",
    "codeQuality": "No linting errors, follows standards"
  },
  "workingSoftware": {
    "demoableFunctionality": "What can be demonstrated",
    "deploymentStatus": "Ready for staging",
    "knownLimitations": "Any incomplete aspects"
  },
  "previousContext": "All prior agent outputs plus implementation details"
}
```

**Task Command**:
```
Use the Task tool to launch the QA/Tester with implementation results to validate functionality against acceptance criteria and ensure quality standards.
```

### 5. QA/Tester → DevOps

**QA/Tester Completion Criteria**:
- [ ] All acceptance criteria validated and passing
- [ ] Regression tests executed and passing
- [ ] Performance testing completed within targets
- [ ] Security testing completed (authentication, authorization, data)
- [ ] User experience validated against requirements
- [ ] Test documentation updated
- [ ] Quality metrics meet or exceed standards

**Auto-Trigger Condition**: When quality validation complete and all tests passing

**Handoff Payload**:
```json
{
  "qualityValidation": {
    "acceptanceCriteriaStatus": "All 15 criteria passing",
    "testExecutionResults": "Unit: 100%, Integration: 100%, E2E: 100%",
    "performanceResults": "Response time: 145ms avg, Memory: stable",
    "securityValidation": "Authentication, authorization, data protection verified"
  },
  "testEvidence": {
    "testReports": "Detailed execution results",
    "coverageReports": "96% overall coverage",
    "performanceReports": "Load testing results",
    "qualityMetrics": "Code quality, maintainability scores"
  },
  "deploymentReadiness": {
    "allTestsPassing": true,
    "performanceAcceptable": true,
    "securityValidated": true,
    "readyForStaging": true
  },
  "previousContext": "Complete development chain context"
}
```

**Task Command**:
```
Use the Task tool to launch the DevOps agent with quality validation results to deploy to staging and prepare for production deployment.
```

### 6. DevOps → Sprint Review (User Interaction)

**DevOps Completion Criteria**:
- [ ] Successfully deployed to staging environment
- [ ] Monitoring and alerting configured
- [ ] Performance monitoring active
- [ ] Security scanning completed
- [ ] Backup and rollback procedures ready
- [ ] Production deployment plan prepared
- [ ] System health validated

**Auto-Trigger Condition**: When staging deployment successful and monitored

**Handoff to User** (Sprint Review):
```json
{
  "deliverable": {
    "workingSoftware": "Deployed and accessible at [staging URL]",
    "featuresCompleted": ["Feature 1", "Feature 2", "Feature 3"],
    "businessValueDelivered": "Specific value achieved",
    "demoScript": "Step-by-step demonstration guide"
  },
  "qualityMetrics": {
    "testCoverage": "96%",
    "performance": "Average response time 145ms",
    "security": "All security scans passed",
    "reliability": "99.9% uptime in staging"
  },
  "nextSteps": {
    "productionDeployment": "Ready when approved",
    "nextIncrement": "Proposed next features",
    "timelineEstimate": "2-3 days for next increment"
  },
  "userActions": [
    "Review working software at staging URL",
    "Validate against your original requirements",
    "Approve for production OR request changes OR add new requirements"
  ]
}
```

**User Interaction Required**: Review and approval of working increment

## Error Handling and Escalation

### Agent Cannot Complete Work

**Scenario**: Agent encounters blocker preventing completion

**Process**:
1. Agent identifies specific blocker and impact
2. Agent requests stakeholder input with clear options
3. Stakeholder provides guidance or clarification
4. Agent continues with new direction or escalates to Scrum Master

**Example User Prompt**:
```
Technical Lead encountered blocker: "LinkedIn has changed their authentication system, making current scraping approach impossible."

Options:
1. Switch to LinkedIn API approach (requires API key, different capabilities)
2. Explore alternative job sites (Indeed, Glassdoor)
3. Implement hybrid approach (API + limited scraping)

Please choose direction: [Your choice and any additional context]
```

### Timeline at Risk

**Scenario**: Sprint timeline cannot be met with current scope

**Process**:
1. Scrum Master identifies timeline risk
2. Automatically presents scope adjustment options
3. User chooses preferred approach
4. Team re-plans and continues

### Quality Standards Not Met

**Scenario**: Quality gates fail (tests, performance, security)

**Process**:
1. QA/Tester or DevOps identifies quality issue
2. Automatically returns to Developer with specific requirements
3. Developer fixes issues and re-submits
4. Process continues when quality standards met

## Monitoring and Progress Tracking

### Automated Progress Updates

**Daily Summary** (Automatically generated):
```
Sprint Progress Update - Day X

Completed Today:
- [Agent]: [Specific accomplishments]
- [Agent]: [Specific accomplishments]

In Progress:
- [Agent]: [Current work and expected completion]

Timeline Status:
- On Track / Ahead / At Risk
- Estimated completion: [Date]

Quality Metrics:
- Test coverage: X%
- Performance: X ms
- No blockers / Blockers: [Description]

Next 24 Hours:
- [Expected progress and milestones]
```

### Context Preservation

**Complete Project Context** maintained throughout:
- Original user requirements and business context
- All agent decisions and rationale
- Code changes and technical decisions
- Quality validation results
- User feedback and change requests

This enables seamless handoffs and maintains project coherence across the entire development process.

## Implementation Notes

Each agent should:
1. **Check completion criteria** before triggering handoff
2. **Use Task tool** to launch next agent with complete context
3. **Preserve all context** from previous agents
4. **Request user input** only when absolutely necessary
5. **Provide clear status updates** for progress tracking

This creates a truly autonomous Agile team that requires minimal user intervention while delivering high-quality, working software incrementally.
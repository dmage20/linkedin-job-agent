# Agile Development Team Agents

This directory contains the configuration and workflows for our simulated Agile software development team using Claude Code agents.

## Team Structure

Our Agile team consists of specialized agents that work together to deliver software incrementally:

### Core Agents

1. **Product Owner** (`agents/product-owner.md`)
   - Defines user stories and acceptance criteria
   - Manages product backlog and prioritization
   - Works with stakeholders to clarify requirements

2. **Scrum Master** (`agents/scrum-master.md`)
   - Facilitates Agile ceremonies (sprint planning, standups, retrospectives)
   - Tracks sprint progress and removes blockers
   - Ensures team follows Agile best practices

3. **Technical Lead** (`agents/technical-lead.md`)
   - Makes architectural decisions
   - Conducts code reviews
   - Provides technical guidance and mentoring

4. **Developer** (`agents/developer.md`)
   - Implements features following TDD practices
   - Writes clean, tested code
   - Collaborates on technical solutions

5. **QA/Tester** (`agents/qa-tester.md`)
   - Creates comprehensive test plans
   - Writes automated tests
   - Validates feature completeness

6. **DevOps** (`agents/devops.md`)
   - Manages CI/CD pipelines
   - Handles deployment and infrastructure
   - Ensures system reliability

## Agile Workflow

### Sprint Cycle (1-2 weeks)

1. **Sprint Planning**: Product Owner presents user stories, team estimates and commits
2. **Daily Development**: Incremental work with daily check-ins
3. **Sprint Review**: Demo completed features for stakeholder feedback
4. **Sprint Retrospective**: Team reflects and improves process

### Test-Driven Development (TDD)

All development follows the Red-Green-Refactor cycle:
- **Red**: Write failing test first
- **Green**: Write minimal code to pass test
- **Refactor**: Improve code while keeping tests passing

### Definition of Done

Features are considered complete when they have:
- [ ] Passing unit tests
- [ ] Integration tests
- [ ] Code review approval
- [ ] Documentation updates
- [ ] Stakeholder acceptance

## Review and Approval Process

### Incremental Delivery

Work is broken into small, testable increments that can be:
1. **Demonstrated** - Show working functionality
2. **Tested** - Validate against acceptance criteria
3. **Reviewed** - Get stakeholder feedback
4. **Approved** - Sign off for next increment

### Change Management

When changes are requested:
1. Product Owner updates user story
2. Scrum Master assesses impact on sprint
3. Team re-estimates and adjusts plan
4. Work continues with new requirements

## File Structure

- `agents/` - Individual agent definitions and capabilities
- `workflows/` - Step-by-step process documentation
- `templates/` - Reusable templates for stories, tests, etc.
- `sprints/` - Sprint-specific tracking and artifacts

## Usage

To start a new feature development:

1. Engage **Product Owner** to define user stories
2. **Scrum Master** facilitates sprint planning
3. **Technical Lead** provides architecture guidance
4. **Developer** implements with TDD approach
5. **QA/Tester** validates functionality
6. **DevOps** handles deployment readiness

Each agent maintains context of the overall project while focusing on their specialized role.
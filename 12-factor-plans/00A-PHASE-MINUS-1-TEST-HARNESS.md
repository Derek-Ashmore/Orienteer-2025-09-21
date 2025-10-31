# Phase -1: Test Harness Foundation
## Establish Comprehensive Testing Before Any Changes (4-6 weeks)

**Phase Duration**: 4-6 weeks
**Priority**: CRITICAL - MUST COMPLETE FIRST
**Prerequisites**: None (starting point)
**Human Involvement**: HIGH - Architecture decisions, test strategy approval

---

## ⚠️ CRITICAL: Why This Phase Comes First

**You CANNOT safely refactor a brownfield application without tests.**

This phase establishes a comprehensive automated test harness that will:
1. **Detect regressions** - Catch broken functionality immediately
2. **Enable safe refactoring** - Change code with confidence
3. **Document behavior** - Tests serve as executable documentation
4. **Prevent production incidents** - Find bugs before deployment
5. **Support continuous integration** - Automated validation on every commit

**Without this foundation, the entire transformation is at risk.**

---

## Phase Objectives

### Primary Goals
1. **Characterization tests** - Capture current behavior as-is
2. **Integration test framework** - Test full system end-to-end
3. **API test suite** - Validate all REST endpoints
4. **Database test fixtures** - Reproducible test data
5. **CI/CD pipeline** - Automated test execution
6. **Test coverage baseline** - Measure what we have

### Success Criteria
- ✅ Integration tests covering all major user workflows
- ✅ API tests for all REST endpoints
- ✅ Database tests with fixtures and rollback
- ✅ CI pipeline runs tests automatically
- ✅ Test coverage baseline documented (aiming for 60%+ initially)
- ✅ Zero failed tests (all tests pass in current state)
- ✅ Test execution under 10 minutes

---

## Human Staffing Requirements

### Core Team (Full-Time for 4-6 weeks)

**Test Architect (1 FTE)**
- Role: Design test strategy and framework
- Responsibilities:
  - Define testing approach for brownfield system
  - Select testing frameworks and tools
  - Design test data management strategy
  - Review and approve test architecture
- Time Commitment: 4-6 weeks full-time
- Skills Required: Test automation, Java, brownfield systems

**Senior QA Engineers (2 FTE)**
- Role: Implement test harness
- Responsibilities:
  - Write characterization tests
  - Create integration test suite
  - Build API test framework
  - Set up test data fixtures
- Time Commitment: 4-6 weeks full-time
- Skills Required: Java, JUnit, REST API testing, database testing

**DevOps Engineer (0.5 FTE)**
- Role: CI/CD pipeline setup
- Responsibilities:
  - Configure automated test execution
  - Set up test environments
  - Implement test reporting
- Time Commitment: 2-3 weeks (50% allocation)
- Skills Required: CI/CD tools, Docker, Kubernetes

### Supporting Team (Part-Time)

**Technical Lead (0.25 FTE)**
- Role: Technical oversight and decisions
- Responsibilities:
  - Review test architecture
  - Approve framework selections
  - Guide team on complex scenarios
- Time Commitment: 1-2 hours per day
- Skills Required: Orienteer architecture knowledge, testing expertise

**Product Manager (0.1 FTE)**
- Role: Define critical user workflows
- Responsibilities:
  - Identify must-test user scenarios
  - Prioritize test coverage areas
  - Review test completeness
- Time Commitment: 2-3 hours per week
- Skills Required: Product knowledge, user workflow understanding

**Domain Experts (2-3, 0.1 FTE each)**
- Role: Subject matter expertise
- Responsibilities:
  - Explain business rules
  - Validate test scenarios
  - Identify edge cases
- Time Commitment: 1-2 hours per week each
- Skills Required: Deep Orienteer domain knowledge

---

## Implementation Tasks

### Task 1: Test Strategy and Framework Selection
**Duration**: 3-5 days
**Human Activity**: Architecture decisions, framework evaluation
**Automation Level**: LOW - Human-driven decisions

#### Human Activities

1. **Test Strategy Workshop (4 hours)**
   - **Participants**: Test Architect, Technical Lead, Senior QA Engineers
   - **Deliverable**: Test strategy document
   - **Decisions Required**:
     - Testing approach (characterization vs. new tests)
     - Framework selections (JUnit, RestAssured, TestContainers)
     - Test data management strategy
     - Coverage targets and priorities

2. **Framework Evaluation (2 days)**
   - **Assigned To**: Test Architect + Senior QA Engineer
   - **Activities**:
     - Evaluate testing frameworks for Java/Wicket
     - Prototype test examples with candidate frameworks
     - Document pros/cons of each option
   - **Deliverable**: Framework recommendation document

3. **Architecture Review (2 hours)**
   - **Participants**: Technical Lead, Test Architect, Tech Team
   - **Deliverable**: Approved test architecture
   - **Decisions Required**:
     - Test environment approach (embedded vs. external DB)
     - Test data fixtures strategy
     - Mock vs. real external services

#### Agentic Support
```markdown
**Claude-Flow Task**: Research testing frameworks for Java/Wicket applications
- Objective: Provide framework options and recommendations
- Deliverable: Comparison matrix of testing frameworks
- Human Decision: Final framework selection
```

#### Deliverables
- [ ] Test strategy document (approved by Technical Lead)
- [ ] Framework selection rationale
- [ ] Test architecture diagram
- [ ] Test data management plan

---

### Task 2: Test Environment Setup
**Duration**: 5-7 days
**Human Activity**: Configuration, troubleshooting
**Automation Level**: MEDIUM - Mix of human and agentic work

#### Human Activities

1. **Environment Configuration (2 days)**
   - **Assigned To**: DevOps Engineer
   - **Activities**:
     - Set up isolated test databases
     - Configure test environment variables
     - Set up Docker Compose for local testing
   - **Deliverable**: Working test environment

2. **CI/CD Pipeline Setup (3 days)**
   - **Assigned To**: DevOps Engineer
   - **Activities**:
     - Configure GitHub Actions or Jenkins
     - Set up automated test execution
     - Configure test reporting (JUnit XML, coverage reports)
     - Set up test failure notifications
   - **Deliverable**: Automated CI pipeline

3. **Troubleshooting Session (ongoing)**
   - **Assigned To**: DevOps Engineer + QA Engineers
   - **Activities**:
     - Debug environment issues
     - Fix test infrastructure problems
     - Optimize test execution time

#### Agentic Support
```markdown
**Claude-Flow Task**: Create CI/CD pipeline configuration
- Objective: Generate GitHub Actions workflow for test automation
- Input: Test commands, environment requirements
- Deliverable: YAML workflow files
- Human Activity: Review, customize, and deploy
```

#### Implementation Steps

1. **Test Database Setup**
   ```yaml
   # docker-compose.test.yml
   version: '3.8'
   services:
     orientdb-test:
       image: orientechnologies/orientdb:3.2.27
       environment:
         ORIENTDB_ROOT_PASSWORD: test_password
       ports:
         - "2424:2424"
       volumes:
         - ./test-data:/orientdb/databases
   ```

2. **CI Pipeline Configuration**
   ```yaml
   # .github/workflows/test.yml
   name: Test Suite

   on:
     push:
       branches: [main, develop]
     pull_request:

   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
       - uses: actions/checkout@v3

       - name: Set up JDK 8
         uses: actions/setup-java@v3
         with:
           java-version: '8'
           distribution: 'temurin'

       - name: Start test database
         run: docker-compose -f docker-compose.test.yml up -d

       - name: Wait for database
         run: ./wait-for-it.sh localhost:2424 -t 60

       - name: Run tests
         run: mvn clean test

       - name: Publish test results
         uses: EnricoMi/publish-unit-test-result-action@v2
         if: always()
         with:
           files: '**/target/surefire-reports/*.xml'

       - name: Upload coverage reports
         uses: codecov/codecov-action@v3
   ```

#### Deliverables
- [ ] Test database running in Docker
- [ ] CI/CD pipeline configured and running
- [ ] Test reporting dashboard accessible
- [ ] Test environment documentation

---

### Task 3: Characterization Tests
**Duration**: 10-15 days
**Human Activity**: CRITICAL - Understanding and documenting current behavior
**Automation Level**: MEDIUM - Humans define scenarios, agents help implement

#### Human Activities

1. **Workflow Identification Workshop (4 hours)**
   - **Participants**: Product Manager, Domain Experts, QA Engineers, Test Architect
   - **Activities**:
     - Identify critical user workflows
     - Map out key business processes
     - Prioritize testing focus areas
   - **Deliverable**: Prioritized list of 20-30 critical workflows

2. **Behavior Documentation (5 days)**
   - **Assigned To**: Senior QA Engineers + Domain Experts
   - **Activities**:
     - Document current behavior step-by-step
     - Identify expected outcomes
     - Capture edge cases and error scenarios
     - Record current bugs/quirks (to preserve!)
   - **Deliverable**: Workflow test specifications

3. **Test Implementation Reviews (ongoing)**
   - **Participants**: Test Architect + Senior QA Engineers
   - **Frequency**: Daily 30-minute reviews
   - **Activities**:
     - Review test code quality
     - Ensure tests capture behavior correctly
     - Identify coverage gaps

#### Agentic Support
```markdown
**Claude-Flow Task**: Generate characterization tests from specifications
- Input: Workflow specifications written by humans
- Objective: Generate test code following patterns
- Deliverable: Test code drafts
- Human Activity: Review, refine, and validate tests
```

#### What Are Characterization Tests?

Characterization tests capture **current behavior as-is**, including:
- ✅ Current functionality (even if suboptimal)
- ✅ Current bugs (yes, we preserve bugs initially!)
- ✅ Current performance characteristics
- ✅ Current data structures

**Purpose**: Create a safety net that detects ANY change in behavior

#### Example Workflow Test

```java
/**
 * Characterization Test: User Login and Browse Data
 *
 * This test captures the CURRENT behavior of the login and data browsing flow.
 * If this test fails after refactoring, we've changed behavior (intentionally or not).
 *
 * Created by: [QA Engineer Name]
 * Reviewed by: [Domain Expert Name]
 * Date: 2025-10-31
 */
@Test
public void testUserLoginAndBrowseData() {
    // GIVEN: Database with test user
    createTestUser("testuser", "password");

    // WHEN: User logs in
    Response loginResponse = given()
        .contentType(ContentType.JSON)
        .body(new LoginRequest("testuser", "password"))
        .when()
        .post("/api/auth/login")
        .then()
        .statusCode(200)
        .extract().response();

    String sessionId = loginResponse.getCookie("JSESSIONID");
    assertNotNull(sessionId, "Session ID should be created");

    // WHEN: User browses data with session
    Response dataResponse = given()
        .cookie("JSESSIONID", sessionId)
        .when()
        .get("/api/data")
        .then()
        .statusCode(200)
        .extract().response();

    // THEN: Verify current behavior (even if not ideal)
    List<DataItem> items = dataResponse.jsonPath().getList("items", DataItem.class);
    assertTrue(items.size() > 0, "Should return some data");

    // Document current behavior: Session is stored in database
    // (This is what we'll change in Phase 2, but for now we verify it works)
    verifySessionInDatabase(sessionId);
}
```

#### Critical Workflows to Test (Minimum 20)

**Authentication & Authorization** (Human-defined priorities):
1. User login with valid credentials
2. User login with invalid credentials
3. User logout
4. Session expiration
5. Role-based access control

**Data Management**:
6. Create new record
7. Read/view record details
8. Update existing record
9. Delete record
10. Search/filter records

**Business Workflows** (Domain Expert input):
11. Complete BPM workflow
12. Generate report
13. Send email notification
14. Import data (ETL)
15. Export data

**Error Handling**:
16. Handle database connection failure
17. Handle validation errors
18. Handle concurrent updates
19. Handle large data sets
20. Handle invalid input

#### Implementation Approach

**Week 1: High-Priority Workflows (Human-led)**
- QA Engineers work with Domain Experts
- Document and implement top 10 workflows
- Daily review meetings

**Week 2: Medium-Priority Workflows (Increasing automation)**
- Establish patterns from Week 1
- Use agentic support to generate similar tests
- Human review and validation

**Week 3: Edge Cases and Error Scenarios**
- Test error conditions
- Test performance characteristics
- Test data integrity

#### Deliverables
- [ ] 20-30 characterization tests implemented
- [ ] All tests passing (capturing current behavior)
- [ ] Test documentation with business context
- [ ] Coverage report showing tested workflows

---

### Task 4: API Test Suite
**Duration**: 7-10 days
**Human Activity**: API contract definition
**Automation Level**: HIGH - Good candidate for agentic implementation

#### Human Activities

1. **API Inventory and Prioritization (1 day)**
   - **Assigned To**: Technical Lead + QA Engineers
   - **Activities**:
     - List all REST endpoints
     - Identify public vs. internal APIs
     - Prioritize critical endpoints
   - **Deliverable**: API endpoint inventory with priorities

2. **API Contract Review (2 days)**
   - **Participants**: Technical Lead, QA Engineers
   - **Activities**:
     - Document expected inputs/outputs
     - Define error scenarios
     - Identify authentication requirements
   - **Deliverable**: API test specifications

3. **Test Review and Sign-off (ongoing)**
   - **Participants**: Technical Lead
   - **Frequency**: Every 2 days
   - **Activities**:
     - Review generated test code
     - Validate test coverage
     - Approve test suite

#### Agentic Support
```markdown
**Claude-Flow Task**: Generate REST API tests from OpenAPI spec or code analysis
- Input: Endpoint list, expected behaviors
- Objective: Generate comprehensive API test suite
- Deliverable: RestAssured test code
- Human Activity: Review, add edge cases, validate
```

#### Implementation Steps

1. **API Discovery (Human + Agent)**
   ```bash
   # Human activity: Review and categorize endpoints
   # Agent activity: Generate endpoint list from code

   # Critical endpoints (must test):
   POST /api/auth/login
   POST /api/auth/logout
   GET /api/data
   POST /api/data
   PUT /api/data/{id}
   DELETE /api/data/{id}
   GET /api/reports
   POST /api/reports/generate
   ```

2. **API Test Framework**
   ```java
   /**
    * Base class for API tests
    *
    * Provides common setup, authentication, and utilities
    */
   @SpringBootTest(webEnvironment = WebEnvironment.RANDOM_PORT)
   public abstract class BaseApiTest {

       @LocalServerPort
       protected int port;

       protected RequestSpecification givenAuthenticated() {
           String token = authenticate("testuser", "password");
           return given()
               .port(port)
               .header("Authorization", "Bearer " + token);
       }

       protected void setupTestData() {
           // Common test data setup
       }

       @AfterEach
       protected void cleanupTestData() {
           // Clean up after each test
       }
   }
   ```

3. **Example API Test**
   ```java
   /**
    * API Tests for Data Endpoints
    *
    * Tests all CRUD operations on /api/data endpoints
    * Validates authentication, authorization, and error handling
    */
   public class DataApiTest extends BaseApiTest {

       @Test
       public void testGetDataRequiresAuthentication() {
           given()
               .port(port)
               .when()
               .get("/api/data")
               .then()
               .statusCode(401);
       }

       @Test
       public void testGetDataReturnsDataForAuthenticatedUser() {
           setupTestData();

           givenAuthenticated()
               .when()
               .get("/api/data")
               .then()
               .statusCode(200)
               .body("size()", greaterThan(0));
       }

       @Test
       public void testCreateDataValidatesInput() {
           Map<String, Object> invalidData = new HashMap<>();
           // Missing required fields

           givenAuthenticated()
               .contentType(ContentType.JSON)
               .body(invalidData)
               .when()
               .post("/api/data")
               .then()
               .statusCode(400)
               .body("error", notNullValue());
       }

       @Test
       public void testUpdateDataRequiresOwnership() {
           // User A creates data
           String dataId = createDataAsUser("userA");

           // User B tries to update
           String tokenUserB = authenticate("userB", "password");

           given()
               .port(port)
               .header("Authorization", "Bearer " + tokenUserB)
               .contentType(ContentType.JSON)
               .body(Map.of("name", "Updated"))
               .when()
               .put("/api/data/" + dataId)
               .then()
               .statusCode(403);
       }
   }
   ```

#### Target Coverage
- [ ] All public REST endpoints (100%)
- [ ] Authentication/authorization tests
- [ ] Input validation tests
- [ ] Error handling tests
- [ ] Happy path + edge cases

#### Deliverables
- [ ] API test suite covering all endpoints
- [ ] API test documentation
- [ ] Test data fixtures for API tests
- [ ] All API tests passing

---

### Task 5: Database Test Foundation
**Duration**: 5-7 days
**Human Activity**: Test data design, data integrity validation
**Automation Level**: MEDIUM

#### Human Activities

1. **Test Data Design Workshop (4 hours)**
   - **Participants**: Database Engineer, Domain Experts, QA Engineers
   - **Activities**:
     - Identify key data entities
     - Design test data fixtures
     - Define data relationships
   - **Deliverable**: Test data design document

2. **Data Integrity Rules Documentation (2 days)**
   - **Assigned To**: Database Engineer + Domain Experts
   - **Activities**:
     - Document current constraints
     - Identify referential integrity rules
     - Document business rules
   - **Deliverable**: Data integrity specifications

3. **Test Data Review (ongoing)**
   - **Participants**: Domain Experts
   - **Activities**:
     - Validate test data realism
     - Ensure edge cases covered
     - Approve test fixtures

#### Implementation Steps

1. **Test Data Fixtures**
   ```java
   /**
    * Test data builder for reproducible test scenarios
    *
    * Provides fluent API for creating test data
    */
   public class TestDataBuilder {

       private ODatabaseSession database;

       public UserBuilder user() {
           return new UserBuilder(database);
       }

       public DataBuilder data() {
           return new DataBuilder(database);
       }

       public void cleanup() {
           // Remove all test data
       }
   }

   // Usage in tests
   @BeforeEach
   public void setupTestData() {
       testData = new TestDataBuilder(database);

       // Create consistent test scenario
       user1 = testData.user()
           .username("testuser1")
           .email("test1@example.com")
           .role("USER")
           .create();

       user2 = testData.user()
           .username("testuser2")
           .email("test2@example.com")
           .role("ADMIN")
           .create();
   }

   @AfterEach
   public void cleanupTestData() {
       testData.cleanup();
   }
   ```

2. **Database Test Pattern**
   ```java
   /**
    * Database tests verify data integrity and business rules
    */
   @TestInstance(TestInstance.Lifecycle.PER_CLASS)
   public class DatabaseIntegrityTest {

       @Test
       public void testUsernameMustBeUnique() {
           testData.user().username("duplicate").create();

           assertThrows(UniqueConstraintException.class, () -> {
               testData.user().username("duplicate").create();
           });
       }

       @Test
       public void testDeleteUserCascadesToRelatedData() {
           ODocument user = testData.user().create();
           ODocument data = testData.data().owner(user).create();

           // Delete user
           database.delete(user.getIdentity());

           // Verify cascade
           assertNull(database.load(data.getIdentity()));
       }
   }
   ```

#### Deliverables
- [ ] Test data builder framework
- [ ] Test data fixtures (10+ scenarios)
- [ ] Database integrity tests
- [ ] Cleanup mechanisms working

---

### Task 6: Test Coverage Analysis and Baseline
**Duration**: 2-3 days
**Human Activity**: Coverage review, gap analysis
**Automation Level**: HIGH - Tooling generates reports

#### Human Activities

1. **Coverage Analysis Session (4 hours)**
   - **Participants**: Test Architect, Technical Lead, QA Engineers
   - **Activities**:
     - Review coverage reports
     - Identify untested critical paths
     - Prioritize coverage improvements
   - **Deliverable**: Coverage improvement plan

2. **Risk Assessment (2 hours)**
   - **Participants**: Technical Lead, Test Architect, Product Manager
   - **Activities**:
     - Identify high-risk, low-coverage areas
     - Assess testing gaps
     - Determine acceptable coverage thresholds
   - **Deliverable**: Testing risk matrix

3. **Sign-off Decision (1 hour)**
   - **Participants**: Technical Lead, Project Manager
   - **Decision**: Is test coverage sufficient to proceed with refactoring?
   - **Go/No-Go**: Proceed to Phase 0 or add more tests

#### Coverage Tools Setup

```xml
<!-- pom.xml - Add JaCoCo for coverage -->
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.10</version>
    <executions>
        <execution>
            <goals>
                <goal>prepare-agent</goal>
            </goals>
        </execution>
        <execution>
            <id>report</id>
            <phase>test</phase>
            <goals>
                <goal>report</goal>
            </goals>
        </execution>
    </executions>
</plugin>
```

#### Coverage Targets

**Phase -1 Targets** (Baseline):
- Integration Tests: 60%+ of critical workflows
- API Tests: 100% of public endpoints
- Unit Tests: 40%+ (lower priority for brownfield)

**Long-term Targets** (Post-refactoring):
- Integration Tests: 80%+
- API Tests: 100%
- Unit Tests: 70%+

#### Deliverables
- [ ] Coverage report generated
- [ ] Coverage baseline documented
- [ ] Coverage improvement plan
- [ ] Go/no-go decision for Phase 0

---

## Human Decision Points

### Week 2: Framework Selection Review
**Decision Maker**: Technical Lead
**Input**: Test Architect recommendation
**Question**: Approve selected testing frameworks?
**Options**: Approve / Request alternatives / Defer

### Week 4: Coverage Adequacy Review
**Decision Maker**: Technical Lead + Project Manager
**Input**: Coverage reports, test inventory
**Question**: Is test coverage sufficient to proceed?
**Options**: Proceed to Phase 0 / Add more tests / Reassess approach

### Week 6: Phase -1 Completion Sign-off
**Decision Maker**: Technical Lead + Project Manager + Product Manager
**Input**: All deliverables, test execution results
**Question**: Approve Phase -1 completion and proceed to Phase 0?
**Options**: Approve / Request additions / Fail Phase -1

---

## Risk Management

### Risks Specific to Phase -1

**Risk: Tests Take Too Long to Run**
- **Mitigation**: Parallelize tests, optimize test data setup
- **Owner**: DevOps Engineer
- **Human Decision Required**: If tests take > 15 minutes, prioritize optimization

**Risk: Tests Are Flaky/Unreliable**
- **Mitigation**: Investigate root causes, add retries where appropriate, fix flaky tests
- **Owner**: QA Engineers
- **Human Decision Required**: Zero tolerance for flaky tests in baseline

**Risk: Coverage Insufficient**
- **Mitigation**: Extend Phase -1 timeline, prioritize critical paths
- **Owner**: Test Architect
- **Human Decision Required**: Go/no-go based on risk assessment

**Risk: Domain Knowledge Gaps**
- **Mitigation**: More time with domain experts, pair programming
- **Owner**: QA Engineers + Domain Experts
- **Human Decision Required**: Identify knowledge gaps early, schedule expert time

---

## Success Metrics

### Quantitative Metrics
- ✅ 20-30 characterization tests implemented and passing
- ✅ 100% of public REST endpoints tested
- ✅ Test execution time < 10 minutes
- ✅ Zero flaky tests (100% reliable)
- ✅ Coverage: 60%+ of critical code paths
- ✅ CI pipeline success rate > 95%

### Qualitative Metrics
- ✅ Team confidence in test suite (survey)
- ✅ Domain experts validate test scenarios
- ✅ Technical lead approves test architecture
- ✅ Tests clearly document current behavior

---

## Phase -1 Completion Checklist

### Technical Deliverables
- [ ] Test framework selected and approved
- [ ] Test environment running reliably
- [ ] CI/CD pipeline executing tests automatically
- [ ] 20-30 characterization tests passing
- [ ] API test suite covering all public endpoints
- [ ] Database test fixtures and integrity tests
- [ ] Coverage baseline documented
- [ ] Test documentation complete

### Human Approvals
- [ ] Test Architect signs off on test architecture
- [ ] Technical Lead approves framework selections
- [ ] Domain Experts validate test scenarios
- [ ] Product Manager confirms critical workflows covered
- [ ] Project Manager approves timeline and budget

### Readiness Gates
- [ ] All tests passing (zero failures)
- [ ] Test execution time acceptable (< 10 minutes)
- [ ] Zero flaky tests
- [ ] Coverage meets minimum threshold (60%+)
- [ ] CI pipeline reliable (> 95% success rate)
- [ ] Team trained on test framework

---

## Transition to Phase 0

**Once Phase -1 is complete**, you have:
1. ✅ Safety net to detect regressions
2. ✅ Automated validation on every change
3. ✅ Documented current behavior
4. ✅ Team confidence to refactor

**Now you can safely proceed to Phase 0** (Security & Quick Wins) knowing that any breaking changes will be caught immediately by the test harness.

---

## Cost Estimate

### Labor Costs (4-6 weeks)

| Role | FTE | Duration | Typical Rate | Cost |
|------|-----|----------|--------------|------|
| Test Architect | 1.0 | 6 weeks | $150-200/hr | $36K-48K |
| Senior QA Engineers (2) | 2.0 | 6 weeks | $120-150/hr | $57.6K-72K |
| DevOps Engineer | 0.5 | 3 weeks | $130-170/hr | $15.6K-20.4K |
| Technical Lead | 0.25 | 6 weeks | $160-200/hr | $9.6K-12K |
| Domain Experts (3) | 0.3 | 6 weeks | $100-130/hr | $7.2K-9.36K |
| **Total Labor** | | | | **$126K-162K** |

### Additional Costs
- CI/CD infrastructure: $500-1000/month
- Testing tools/licenses: $2K-5K
- Training: $3K-5K

**Total Phase -1 Investment**: $130K-170K

---

## Why This Investment Is Worth It

**Without Phase -1**:
- ❌ High risk of breaking production
- ❌ Slow, manual validation
- ❌ Fear of making changes
- ❌ Regressions discovered by customers

**With Phase -1**:
- ✅ Confident refactoring
- ✅ Fast feedback (< 10 minutes)
- ✅ Regressions caught before production
- ✅ Reduced long-term maintenance costs

**ROI**: Prevents 1-2 major production incidents = investment paid back

---

**Next Phase**: [Phase 0 - Security & Quick Wins](01-PHASE-0-SECURITY-QUICK-WINS.md)

**Note**: Do not proceed to Phase 0 until Phase -1 is complete and approved.

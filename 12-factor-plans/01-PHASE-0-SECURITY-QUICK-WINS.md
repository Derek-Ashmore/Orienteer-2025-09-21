# Phase 0: Security & Quick Wins Implementation Plan
## Critical Security Fixes and Foundation (2-3 weeks)

**Phase Duration**: 2-3 weeks
**Priority**: CRITICAL
**12-Factor Focus**: III (Config), IX (Disposability), XI (Logs)
**Agent Teams**: 2-3 concurrent teams
**Prerequisites**: None (starting point)

---

## Phase Objectives

### Primary Goals
1. **Eliminate ALL hardcoded credentials** - Security vulnerability remediation
2. **Implement graceful shutdown** - Prevent data loss during scaling
3. **Add health check endpoints** - Enable cloud orchestration
4. **Implement structured logging** - Improve observability
5. **Set up secrets management** - Enable secure configuration

### Success Criteria
- ✅ Zero hardcoded credentials in codebase (security scan passes)
- ✅ Health endpoints respond in <100ms
- ✅ Graceful shutdown completes in <30 seconds
- ✅ 100% structured JSON logging
- ✅ Secrets manager integration functional
- ✅ All existing functionality preserved (regression tests pass)

---

## Implementation Tasks

### Task 1: Remove Hardcoded Credentials
**12-Factor**: III (Config)
**Priority**: CRITICAL
**Estimated Effort**: 3-5 days
**Agent Team**: Security + Backend agents

#### Current Issues
```properties
# orienteer-core/src/main/resources/orienteer-default.properties
orientdb.guest.username=reader
orientdb.guest.password=reader
orientdb.admin.username=admin
orientdb.admin.password=admin
orientdb.root.password=root

# Other files with credentials
mail.smtp.password=hardcoded_password
twilio.auth.token=hardcoded_token
```

#### Implementation Steps

1. **Identify All Credential Locations** (Agent: Security)
   ```bash
   # Claude Code Task tool spawns security agent:
   Task("Security Scanner", "
     1. Scan codebase for hardcoded credentials using patterns:
        - grep -r 'password.*=' --include='*.properties'
        - grep -r 'username.*=' --include='*.properties'
        - Use semantic analysis to find credential patterns
     2. Create inventory of all credentials found
     3. Store inventory in memory: swarm/security/credentials-inventory
   ", "security-manager")
   ```

2. **Create Environment Variable Configuration System** (Agent: Backend)
   ```java
   // New class: orienteer-core/.../config/EnvironmentConfigLoader.java
   public class EnvironmentConfigLoader {
       /**
        * Load configuration value with environment variable override
        * Priority: ENV_VAR > System Property > Default
        */
       public static String getConfig(String key, String defaultValue) {
           // 1. Check environment variable
           String envKey = key.toUpperCase().replace('.', '_');
           String envValue = System.getenv(envKey);
           if (envValue != null && !envValue.isEmpty()) {
               return envValue;
           }

           // 2. Check system property
           String sysProp = System.getProperty(key);
           if (sysProp != null && !sysProp.isEmpty()) {
               return sysProp;
           }

           // 3. Return default (should be null for credentials)
           return defaultValue;
       }

       /**
        * Require configuration value - fail fast if missing
        */
       public static String requireConfig(String key) {
           String value = getConfig(key, null);
           if (value == null || value.isEmpty()) {
               throw new ConfigurationException(
                   "Required configuration missing: " + key +
                   "\nSet environment variable: " +
                   key.toUpperCase().replace('.', '_')
               );
           }
           return value;
       }
   }
   ```

3. **Update Configuration Files** (Agent: Backend)
   ```properties
   # orienteer-default.properties - REMOVE all credential values
   # Replace with comments showing required environment variables

   # OrientDB Configuration
   # Required environment variables:
   # ORIENTDB_GUEST_USERNAME - Guest user username
   # ORIENTDB_GUEST_PASSWORD - Guest user password (use secrets manager)
   # ORIENTDB_ADMIN_USERNAME - Admin username
   # ORIENTDB_ADMIN_PASSWORD - Admin password (use secrets manager)

   # DO NOT set default values for credentials
   orientdb.guest.username=
   orientdb.guest.password=
   orientdb.admin.username=
   orientdb.admin.password=
   ```

4. **Update Application Code** (Agent: Backend)
   ```java
   // orienteer-core/.../OrientDbSettings.java
   public class OrientDbSettings {
       public void loadCredentials() {
           // OLD (REMOVE):
           // String adminUser = properties.getProperty("orientdb.admin.username", "admin");

           // NEW (ADD):
           String adminUser = EnvironmentConfigLoader.requireConfig(
               "orientdb.admin.username"
           );
           String adminPassword = EnvironmentConfigLoader.requireConfig(
               "orientdb.admin.password"
           );

           // Validate credentials are not default values
           validateCredentials(adminUser, adminPassword);
       }

       private void validateCredentials(String user, String pass) {
           if ("admin".equals(user) || "admin".equals(pass) ||
               "root".equals(pass) || "reader".equals(pass)) {
               throw new SecurityException(
                   "Default credentials detected. Use secure credentials in production."
               );
           }
       }
   }
   ```

5. **Create Environment Template** (Agent: Documentation)
   ```bash
   # .env.example - Template for environment variables
   # Copy to .env and fill in secure values

   # OrientDB Credentials (REQUIRED)
   ORIENTDB_ADMIN_USERNAME=your_admin_username
   ORIENTDB_ADMIN_PASSWORD=your_secure_password
   ORIENTDB_GUEST_USERNAME=your_guest_username
   ORIENTDB_GUEST_PASSWORD=your_guest_password

   # Database Connection (REQUIRED)
   ORIENTDB_URL=remote:orientdb-server:2424/Orienteer

   # Mail Server (OPTIONAL)
   MAIL_SMTP_HOST=smtp.example.com
   MAIL_SMTP_PORT=587
   MAIL_SMTP_USERNAME=your_email@example.com
   MAIL_SMTP_PASSWORD=your_email_password

   # Twilio Integration (OPTIONAL)
   TWILIO_ACCOUNT_SID=your_account_sid
   TWILIO_AUTH_TOKEN=your_auth_token
   ```

6. **Create Docker Secret Support** (Agent: DevOps)
   ```dockerfile
   # Dockerfile update
   FROM openjdk:8-jre-slim

   # Support Docker secrets
   ENV ORIENTDB_ADMIN_PASSWORD_FILE=/run/secrets/orientdb_admin_password
   ENV ORIENTDB_ADMIN_USERNAME_FILE=/run/secrets/orientdb_admin_username

   # Enhanced entry point to load secrets
   COPY docker-entrypoint.sh /
   RUN chmod +x /docker-entrypoint.sh
   ENTRYPOINT ["/docker-entrypoint.sh"]
   ```

   ```bash
   #!/bin/bash
   # docker-entrypoint.sh

   # Load secrets from files if available
   if [ -f "$ORIENTDB_ADMIN_PASSWORD_FILE" ]; then
       export ORIENTDB_ADMIN_PASSWORD=$(cat "$ORIENTDB_ADMIN_PASSWORD_FILE")
   fi

   if [ -f "$ORIENTDB_ADMIN_USERNAME_FILE" ]; then
       export ORIENTDB_ADMIN_USERNAME=$(cat "$ORIENTDB_ADMIN_USERNAME_FILE")
   fi

   # Start application
   exec java $JAVA_OPTS -jar /app/orienteer.jar "$@"
   ```

7. **Update Tests** (Agent: Testing)
   ```java
   // EnvironmentConfigLoaderTest.java
   @Test
   public void testRequiredConfigThrowsExceptionWhenMissing() {
       // Clear environment
       clearSystemProperty("test.config");
       clearEnvironmentVariable("TEST_CONFIG");

       assertThrows(ConfigurationException.class, () -> {
           EnvironmentConfigLoader.requireConfig("test.config");
       });
   }

   @Test
   public void testDefaultCredentialsRejected() {
       System.setenv("ORIENTDB_ADMIN_PASSWORD", "admin");

       assertThrows(SecurityException.class, () -> {
           new OrientDbSettings().loadCredentials();
       });
   }
   ```

#### Agent Coordination
```javascript
// Single message with parallel agent spawning
[Concurrent Execution]:
  Task("Security Scanner", "Scan for all hardcoded credentials", "security-manager")
  Task("Backend Developer", "Implement EnvironmentConfigLoader", "backend-dev")
  Task("DevOps Engineer", "Create Docker secrets support", "cicd-engineer")
  Task("Test Engineer", "Write tests for config loading", "tester")
  Task("Documentation", "Create .env.example template", "reviewer")
```

---

### Task 2: Implement Graceful Shutdown
**12-Factor**: IX (Disposability)
**Priority**: CRITICAL
**Estimated Effort**: 2-3 days
**Agent Team**: Backend + DevOps agents

#### Current Issue
```java
// ServerRunner.java - No shutdown handling
public class ServerRunner {
    public void start() {
        server.start();
        // Missing: shutdown hooks
        // Missing: connection draining
        // Missing: in-flight request handling
    }
}
```

#### Implementation Steps

1. **Implement Shutdown Hook** (Agent: Backend)
   ```java
   // orienteer-core/.../server/GracefulShutdownHandler.java
   public class GracefulShutdownHandler {
       private final Server server;
       private final AtomicBoolean shuttingDown = new AtomicBoolean(false);
       private final CountDownLatch shutdownComplete = new CountDownLatch(1);

       public void registerShutdownHook() {
           Runtime.getRuntime().addShutdownHook(new Thread(() -> {
               log.info("Shutdown signal received, beginning graceful shutdown");
               gracefulShutdown();
           }, "shutdown-hook"));
       }

       public void gracefulShutdown() {
           if (!shuttingDown.compareAndSet(false, true)) {
               log.warn("Shutdown already in progress");
               return;
           }

           try {
               // Step 1: Stop accepting new requests
               log.info("Step 1: Stopping new request acceptance");
               stopAcceptingRequests();

               // Step 2: Wait for in-flight requests (max 20 seconds)
               log.info("Step 2: Waiting for in-flight requests");
               waitForInFlightRequests(20, TimeUnit.SECONDS);

               // Step 3: Close database connections
               log.info("Step 3: Closing database connections");
               closeDatabaseConnections();

               // Step 4: Stop background tasks
               log.info("Step 4: Stopping background tasks");
               stopBackgroundTasks();

               // Step 5: Stop server
               log.info("Step 5: Stopping server");
               server.stop();

               log.info("Graceful shutdown complete");
           } catch (Exception e) {
               log.error("Error during graceful shutdown", e);
           } finally {
               shutdownComplete.countDown();
           }
       }

       private void stopAcceptingRequests() {
           // Mark server as not ready for health checks
           HealthCheckService.setReady(false);
       }

       private void waitForInFlightRequests(long timeout, TimeUnit unit) {
           RequestTracker tracker = RequestTracker.getInstance();
           long deadline = System.currentTimeMillis() + unit.toMillis(timeout);

           while (tracker.getActiveRequests() > 0 &&
                  System.currentTimeMillis() < deadline) {
               log.debug("Waiting for {} active requests",
                   tracker.getActiveRequests());
               try {
                   Thread.sleep(100);
               } catch (InterruptedException e) {
                   Thread.currentThread().interrupt();
                   break;
               }
           }

           if (tracker.getActiveRequests() > 0) {
               log.warn("Shutdown proceeding with {} active requests",
                   tracker.getActiveRequests());
           }
       }
   }
   ```

2. **Implement Request Tracking** (Agent: Backend)
   ```java
   // orienteer-core/.../server/RequestTracker.java
   public class RequestTracker {
       private static final RequestTracker INSTANCE = new RequestTracker();
       private final AtomicInteger activeRequests = new AtomicInteger(0);

       public static RequestTracker getInstance() {
           return INSTANCE;
       }

       public void requestStarted() {
           activeRequests.incrementAndGet();
       }

       public void requestCompleted() {
           activeRequests.decrementAndGet();
       }

       public int getActiveRequests() {
           return activeRequests.get();
       }
   }

   // Wicket request cycle listener
   public class RequestTrackingListener implements IRequestCycleListener {
       @Override
       public void onBeginRequest(RequestCycle cycle) {
           RequestTracker.getInstance().requestStarted();
       }

       @Override
       public void onEndRequest(RequestCycle cycle) {
           RequestTracker.getInstance().requestCompleted();
       }
   }
   ```

3. **Update Server Runner** (Agent: Backend)
   ```java
   // orienteer-core/.../StartStandalone.java
   public class StartStandalone {
       public static void main(String[] args) {
           Server server = createServer();

           // Register graceful shutdown
           GracefulShutdownHandler shutdownHandler =
               new GracefulShutdownHandler(server);
           shutdownHandler.registerShutdownHook();

           // Register request tracking
           application.getRequestCycleListeners().add(
               new RequestTrackingListener()
           );

           server.start();
           server.join();
       }
   }
   ```

4. **Create Kubernetes Pre-Stop Hook** (Agent: DevOps)
   ```yaml
   # k8s/deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: orienteer
   spec:
     template:
       spec:
         containers:
         - name: orienteer
           lifecycle:
             preStop:
               exec:
                 command:
                 - /bin/sh
                 - -c
                 - |
                   # Notify load balancer we're shutting down
                   curl -X POST http://localhost:8080/admin/shutdown
                   # Wait for graceful shutdown
                   sleep 5
           terminationGracePeriodSeconds: 30
   ```

5. **Add Shutdown Endpoint** (Agent: Backend)
   ```java
   // orienteer-core/.../rest/ShutdownResource.java
   @Path("/admin/shutdown")
   public class ShutdownResource {
       @POST
       @Produces(MediaType.APPLICATION_JSON)
       public Response initiateShutdown() {
           // Verify authentication and authorization
           if (!isAuthorized()) {
               return Response.status(403).build();
           }

           // Start graceful shutdown asynchronously
           new Thread(() -> {
               try {
                   Thread.sleep(100); // Allow response to send
                   GracefulShutdownHandler.getInstance().gracefulShutdown();
               } catch (InterruptedException e) {
                   Thread.currentThread().interrupt();
               }
           }).start();

           return Response.ok()
               .entity("{\"status\": \"shutdown initiated\"}")
               .build();
       }
   }
   ```

6. **Write Tests** (Agent: Testing)
   ```java
   // GracefulShutdownTest.java
   @Test
   public void testShutdownWaitsForInFlightRequests() {
       // Start server
       server.start();

       // Create in-flight requests
       CountDownLatch requestLatch = new CountDownLatch(5);
       for (int i = 0; i < 5; i++) {
           startLongRunningRequest(requestLatch);
       }

       // Initiate shutdown
       long startTime = System.currentTimeMillis();
       shutdownHandler.gracefulShutdown();
       long duration = System.currentTimeMillis() - startTime;

       // Verify all requests completed
       assertEquals(0, requestLatch.getCount());

       // Verify shutdown waited
       assertTrue(duration >= 1000); // At least 1 second
   }
   ```

---

### Task 3: Implement Health Check Endpoints
**12-Factor**: IX (Disposability) + Cloud Enablement
**Priority**: HIGH
**Estimated Effort**: 1-2 days
**Agent Team**: Backend + DevOps agents

#### Implementation Steps

1. **Create Health Check Service** (Agent: Backend)
   ```java
   // orienteer-core/.../health/HealthCheckService.java
   public class HealthCheckService {
       private static final AtomicBoolean ready = new AtomicBoolean(true);
       private static final AtomicBoolean alive = new AtomicBoolean(true);

       public static HealthStatus getHealth() {
           HealthStatus status = new HealthStatus();
           status.setAlive(alive.get());
           status.setReady(ready.get());

           // Check database connectivity
           status.addCheck("database", checkDatabase());

           // Check memory
           status.addCheck("memory", checkMemory());

           // Check disk space
           status.addCheck("disk", checkDiskSpace());

           return status;
       }

       private static CheckResult checkDatabase() {
           try {
               ODatabaseSession db = getDatabase();
               db.query("SELECT FROM OUser LIMIT 1");
               db.close();
               return CheckResult.healthy();
           } catch (Exception e) {
               return CheckResult.unhealthy(e.getMessage());
           }
       }

       private static CheckResult checkMemory() {
           Runtime runtime = Runtime.getRuntime();
           long used = runtime.totalMemory() - runtime.freeMemory();
           long max = runtime.maxMemory();
           double usagePercent = (double) used / max * 100;

           if (usagePercent > 90) {
               return CheckResult.unhealthy(
                   "Memory usage: " + String.format("%.1f%%", usagePercent)
               );
           }
           return CheckResult.healthy();
       }

       public static void setReady(boolean isReady) {
           ready.set(isReady);
       }

       public static void setAlive(boolean isAlive) {
           alive.set(isAlive);
       }
   }
   ```

2. **Create Health Endpoints** (Agent: Backend)
   ```java
   // orienteer-core/.../rest/HealthResource.java
   @Path("/health")
   public class HealthResource {
       /**
        * Liveness probe - is application running?
        * Returns 200 if application is alive, 503 if not
        */
       @GET
       @Path("/live")
       @Produces(MediaType.APPLICATION_JSON)
       public Response liveness() {
           HealthStatus status = HealthCheckService.getHealth();

           if (status.isAlive()) {
               return Response.ok(status).build();
           } else {
               return Response.status(503).entity(status).build();
           }
       }

       /**
        * Readiness probe - is application ready to serve traffic?
        * Returns 200 if ready, 503 if not ready
        */
       @GET
       @Path("/ready")
       @Produces(MediaType.APPLICATION_JSON)
       public Response readiness() {
           HealthStatus status = HealthCheckService.getHealth();

           if (status.isReady()) {
               return Response.ok(status).build();
           } else {
               return Response.status(503).entity(status).build();
           }
       }

       /**
        * Detailed health check (authenticated)
        */
       @GET
       @Produces(MediaType.APPLICATION_JSON)
       public Response health() {
           if (!isAuthorized()) {
               return Response.status(403).build();
           }

           HealthStatus status = HealthCheckService.getHealth();
           return Response.ok(status).build();
       }
   }
   ```

3. **Update Kubernetes Configuration** (Agent: DevOps)
   ```yaml
   # k8s/deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   spec:
     template:
       spec:
         containers:
         - name: orienteer
           livenessProbe:
             httpGet:
               path: /health/live
               port: 8080
             initialDelaySeconds: 60
             periodSeconds: 10
             timeoutSeconds: 5
             failureThreshold: 3

           readinessProbe:
             httpGet:
               path: /health/ready
               port: 8080
             initialDelaySeconds: 30
             periodSeconds: 5
             timeoutSeconds: 3
             failureThreshold: 2
   ```

---

### Task 4: Implement Structured JSON Logging
**12-Factor**: XI (Logs)
**Priority**: HIGH
**Estimated Effort**: 2-3 days
**Agent Team**: Backend agent

#### Implementation Steps

1. **Configure JSON Logging** (Agent: Backend)
   ```xml
   <!-- log4j2.xml -->
   <?xml version="1.0" encoding="UTF-8"?>
   <Configuration status="warn" packages="org.orienteer.core.logging">
       <Appenders>
           <!-- JSON Console Appender -->
           <Console name="JsonConsole" target="SYSTEM_OUT">
               <JsonTemplateLayout eventTemplateUri="classpath:EcsLayout.json"/>
           </Console>
       </Appenders>

       <Loggers>
           <Root level="info">
               <AppenderRef ref="JsonConsole"/>
           </Root>
       </Loggers>
   </Configuration>
   ```

2. **Add JSON Layout Dependency** (Agent: Backend)
   ```xml
   <!-- pom.xml -->
   <dependency>
       <groupId>org.apache.logging.log4j</groupId>
       <artifactId>log4j-layout-template-json</artifactId>
       <version>2.17.1</version>
   </dependency>
   ```

3. **Remove System.out Usage** (Agent: Backend)
   ```java
   // Find and replace all System.out.println with logger

   // OLD (REMOVE):
   System.out.println("Starting server on port: " + port);

   // NEW (ADD):
   private static final Logger log = LoggerFactory.getLogger(StartServer.class);
   log.info("Starting server on port: {}", port);
   ```

4. **Add Request Context Logging** (Agent: Backend)
   ```java
   // orienteer-core/.../logging/RequestContextFilter.java
   public class RequestContextFilter implements IRequestCycleListener {
       @Override
       public void onBeginRequest(RequestCycle cycle) {
           // Add request ID to MDC
           String requestId = UUID.randomUUID().toString();
           MDC.put("requestId", requestId);
           MDC.put("sessionId", cycle.getRequest().getSession().getId());

           // Add to response header for tracing
           cycle.getResponse().setHeader("X-Request-ID", requestId);
       }

       @Override
       public void onEndRequest(RequestCycle cycle) {
           // Clear MDC
           MDC.clear();
       }
   }
   ```

---

### Task 5: Secrets Management Integration
**12-Factor**: III (Config)
**Priority**: HIGH
**Estimated Effort**: 2-3 days
**Agent Team**: Security + DevOps agents

#### Implementation Steps

1. **Create Secrets Manager Interface** (Agent: Security)
   ```java
   // orienteer-core/.../secrets/SecretsManager.java
   public interface SecretsManager {
       String getSecret(String key);
       void refreshSecrets();
   }

   // Environment variable implementation
   public class EnvSecretsManager implements SecretsManager {
       @Override
       public String getSecret(String key) {
           return EnvironmentConfigLoader.requireConfig(key);
       }
   }

   // HashiCorp Vault implementation
   public class VaultSecretsManager implements SecretsManager {
       private final VaultTemplate vaultTemplate;

       @Override
       public String getSecret(String key) {
           VaultResponse response = vaultTemplate.read(
               "secret/orienteer/" + key
           );
           return response.getData().get(key).toString();
       }
   }
   ```

2. **Create Secrets Configuration** (Agent: DevOps)
   ```yaml
   # secrets-config.yaml
   secrets:
     provider: vault  # or: env, aws-secrets-manager, azure-keyvault
     vault:
       address: ${VAULT_ADDR}
       token: ${VAULT_TOKEN}
       namespace: ${VAULT_NAMESPACE:orienteer}
     refresh:
       enabled: true
       interval: 300s  # Refresh every 5 minutes
   ```

---

## Agent Coordination Plan

### Swarm Initialization
```javascript
[Single Message - All agent spawning]:
  // Claude Code Task tool spawns ALL agents concurrently
  Task("Security Lead", "
    Coordinate security fixes across all tasks.
    Use hooks: pre-task, post-edit, post-task.
    Store findings in memory: swarm/security/*
  ", "security-manager")

  Task("Backend Developer 1", "
    Implement EnvironmentConfigLoader and credential removal.
    Coordinate with Security Lead via memory.
  ", "backend-dev")

  Task("Backend Developer 2", "
    Implement graceful shutdown and request tracking.
    Store progress in memory: swarm/shutdown/*
  ", "backend-dev")

  Task("Backend Developer 3", "
    Implement health checks and JSON logging.
  ", "backend-dev")

  Task("DevOps Engineer", "
    Create Docker secrets support and K8s manifests.
    Coordinate with Backend team via hooks.
  ", "cicd-engineer")

  Task("Test Engineer", "
    Write tests for all new functionality.
    Ensure 85%+ coverage.
  ", "tester")

  Task("Reviewer", "
    Code review and documentation.
    Generate runbooks and migration guides.
  ", "reviewer")

  // Batch ALL todos in ONE call
  TodoWrite { todos: [
    {content: "Scan for hardcoded credentials", status: "pending"},
    {content: "Implement EnvironmentConfigLoader", status: "pending"},
    {content: "Remove all credential defaults", status: "pending"},
    {content: "Create .env.example template", status: "pending"},
    {content: "Implement graceful shutdown", status: "pending"},
    {content: "Add request tracking", status: "pending"},
    {content: "Create health check endpoints", status: "pending"},
    {content: "Configure JSON logging", status: "pending"},
    {content: "Remove System.out usage", status: "pending"},
    {content: "Implement secrets manager", status: "pending"},
    {content: "Write comprehensive tests", status: "pending"},
    {content: "Update documentation", status: "pending"}
  ]}
```

---

## Testing Requirements

### Unit Tests (Agent: Testing)
- EnvironmentConfigLoader with various configurations
- GracefulShutdownHandler shutdown scenarios
- HealthCheckService all health checks
- Secrets manager implementations

### Integration Tests (Agent: Testing)
- End-to-end credential loading from environment
- Graceful shutdown with active requests
- Health check endpoints returning correct status
- JSON logging output format validation

### Security Tests (Agent: Security)
- No hardcoded credentials scan passes
- Default credentials rejected
- Secrets rotation works correctly
- Authentication on admin endpoints

### Performance Tests (Agent: Performance)
- Health checks respond in <100ms
- Graceful shutdown completes in <30s
- Logging overhead <5%

---

## Deliverables Checklist

- [ ] All hardcoded credentials removed from codebase
- [ ] EnvironmentConfigLoader implemented and tested
- [ ] .env.example template created
- [ ] Docker secrets support added
- [ ] Graceful shutdown implemented with SIGTERM handling
- [ ] Request tracking operational
- [ ] Health check endpoints (/health/live, /health/ready)
- [ ] Kubernetes probes configured
- [ ] JSON logging configured
- [ ] All System.out.println removed
- [ ] Request context logging (requestId, sessionId)
- [ ] Secrets manager interface and implementations
- [ ] Unit tests: 85%+ coverage
- [ ] Integration tests passing
- [ ] Security scan passing (no credentials found)
- [ ] Documentation updated
- [ ] Migration guide created

---

## Rollout Plan

### Week 1: Development
- Days 1-2: Credential removal and environment config
- Days 3-4: Graceful shutdown implementation
- Day 5: Health checks and logging

### Week 2: Testing and Refinement
- Days 1-2: Comprehensive testing
- Days 3-4: Security validation
- Day 5: Documentation and review

### Week 3: Deployment Preparation
- Days 1-2: Staging deployment
- Days 3-4: Validation and fixes
- Day 5: Production readiness review

---

## Success Validation

### Automated Checks
```bash
# Security scan
npx snyk test
grep -r "password.*=" --include="*.properties" | grep -v ".example"

# Health check validation
curl http://localhost:8080/health/live
curl http://localhost:8080/health/ready

# Graceful shutdown test
kill -TERM <pid>
# Should complete in <30 seconds with no errors

# Log format validation
docker logs orienteer | jq .  # Should parse as JSON
```

### Manual Validation
- [ ] Application starts without credentials in properties files
- [ ] Application fails to start with missing required env vars
- [ ] Health checks return proper status codes
- [ ] Graceful shutdown waits for in-flight requests
- [ ] All logs are in JSON format
- [ ] Secrets can be rotated without code changes

---

## Next Phase

Upon successful completion of Phase 0:
- **Phase 1**: [Configuration & Infrastructure](02-PHASE-1-CONFIGURATION-INFRASTRUCTURE.md)
- Focus: Complete externalization and backing services
- Timeline: 4-6 weeks

---

**Phase Owner**: Security Lead + DevOps Lead
**Review Frequency**: Daily standups, weekly phase review
**Escalation Path**: Project Coordinator → Technical Lead → Stakeholders

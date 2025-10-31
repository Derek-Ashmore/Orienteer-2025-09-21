# Phase 1: Configuration & Infrastructure Implementation Plan
## Complete Externalization and Backing Services (4-6 weeks)

**Phase Duration**: 4-6 weeks
**Priority**: HIGH
**12-Factor Focus**: III (Config), IV (Backing Services), V (Build/Release/Run)
**Agent Teams**: 3-4 concurrent teams
**Prerequisites**: Phase 0 complete (security fixes deployed)

---

## Phase Objectives

### Primary Goals
1. **Complete configuration externalization** - Zero config in code/containers
2. **External backing services** - OrientDB, Redis, message queue
3. **Environment-agnostic builds** - Same artifact across all environments
4. **Service discovery and circuit breakers** - Resilient service connections
5. **Container optimization** - Fast startup, small images

### Success Criteria
- ✅ Zero configuration in code or build artifacts
- ✅ Application runs identically in dev/staging/prod with same container
- ✅ Database switchable via environment variables only
- ✅ Container startup under 60 seconds
- ✅ Circuit breakers prevent cascade failures
- ✅ Health checks show backing service status

---

## Implementation Tasks

### Task 1: Complete Configuration Externalization
**12-Factor**: III (Config)
**Priority**: CRITICAL
**Estimated Effort**: 5-7 days
**Agent Team**: Backend + DevOps agents

#### Implementation Steps

1. **Audit All Configuration** (Agent: Backend)
   ```bash
   # Find all configuration files
   find . -name "*.properties" -o -name "*.xml" -o -name "*.yaml"

   # Analyze configuration categories:
   # - Database connection strings
   # - Port bindings
   # - Feature flags
   # - Integration endpoints
   # - Timeouts and limits
   ```

2. **Create Configuration Schema** (Agent: Backend)
   ```java
   // orienteer-core/.../config/ApplicationConfig.java
   /**
    * Centralized configuration with validation
    * All values loaded from environment variables
    */
   public class ApplicationConfig {
       // Database Configuration
       @Required
       private String orientdbUrl;  // ORIENTDB_URL

       @Required
       private String orientdbUsername;  // ORIENTDB_USERNAME

       @Required
       @Secret
       private String orientdbPassword;  // ORIENTDB_PASSWORD

       private int orientdbPoolMin = 10;  // ORIENTDB_POOL_MIN
       private int orientdbPoolMax = 50;  // ORIENTDB_POOL_MAX

       // Server Configuration
       private String serverHost = "0.0.0.0";  // SERVER_HOST
       private int serverPort = 8080;  // SERVER_PORT
       private int serverMaxThreads = 200;  // SERVER_MAX_THREADS

       // Session Configuration (Phase 2 prep)
       private String sessionStore = "redis";  // SESSION_STORE (redis|memory)
       private String redisUrl;  // REDIS_URL
       private int sessionTimeoutMinutes = 30;  // SESSION_TIMEOUT_MINUTES

       // Feature Flags
       private boolean productionMode = false;  // PRODUCTION_MODE
       private boolean devMode = false;  // DEV_MODE

       // Integration Services
       private String mailSmtpHost;  // MAIL_SMTP_HOST
       private int mailSmtpPort = 587;  // MAIL_SMTP_PORT
       private boolean mailSmtpTls = true;  // MAIL_SMTP_TLS

       /**
        * Load and validate configuration
        */
       public static ApplicationConfig load() {
           ApplicationConfig config = new ApplicationConfig();

           // Load all fields from environment
           for (Field field : ApplicationConfig.class.getDeclaredFields()) {
               loadField(config, field);
           }

           // Validate required fields
           config.validate();

           return config;
       }

       private void validate() {
           List<String> missing = new ArrayList<>();

           // Check all @Required fields
           for (Field field : this.getClass().getDeclaredFields()) {
               if (field.isAnnotationPresent(Required.class)) {
                   try {
                       Object value = field.get(this);
                       if (value == null || value.toString().isEmpty()) {
                           missing.add(field.getName());
                       }
                   } catch (IllegalAccessException e) {
                       throw new RuntimeException(e);
                   }
               }
           }

           if (!missing.isEmpty()) {
               throw new ConfigurationException(
                   "Required configuration missing: " + missing +
                   "\nEnsure all required environment variables are set."
               );
           }
       }
   }
   ```

3. **Remove Embedded Configuration** (Agent: Backend)
   ```properties
   # orienteer-default.properties - BEFORE
   orientdb.url=plocal:./databases/Orienteer
   orientdb.admin.username=admin
   server.port=8080

   # orienteer-default.properties - AFTER (minimal defaults, no credentials)
   # All configuration via environment variables
   # See config-schema.md for required variables
   ```

4. **Create Configuration Documentation** (Agent: Documentation)
   ```markdown
   # Configuration Reference

   ## Required Environment Variables

   ### Database
   - `ORIENTDB_URL` - Database connection URL
     - Example: `remote:orientdb-server:2424/Orienteer`
     - Required: YES
   - `ORIENTDB_USERNAME` - Database username
   - `ORIENTDB_PASSWORD` - Database password (use secrets manager)

   ### Server
   - `SERVER_PORT` - HTTP port (default: 8080)
   - `SERVER_HOST` - Bind host (default: 0.0.0.0)

   ### Session Store (Phase 2)
   - `SESSION_STORE` - Session storage (redis|memory, default: redis)
   - `REDIS_URL` - Redis connection URL (required if SESSION_STORE=redis)

   ## Environment-Specific Examples

   ### Development
   ```bash
   ORIENTDB_URL=remote:localhost:2424/Orienteer
   ORIENTDB_USERNAME=dev_user
   ORIENTDB_PASSWORD=dev_password
   PRODUCTION_MODE=false
   DEV_MODE=true
   ```

   ### Production
   ```bash
   ORIENTDB_URL=remote:orientdb-prod.example.com:2424/Orienteer
   ORIENTDB_USERNAME=prod_user
   ORIENTDB_PASSWORD=${VAULT:orientdb-password}
   PRODUCTION_MODE=true
   DEV_MODE=false
   SESSION_STORE=redis
   REDIS_URL=redis://redis-cluster.example.com:6379
   ```
   ```

5. **Configuration Validation Tool** (Agent: DevOps)
   ```bash
   #!/bin/bash
   # validate-config.sh - Validate configuration before startup

   REQUIRED_VARS=(
       "ORIENTDB_URL"
       "ORIENTDB_USERNAME"
       "ORIENTDB_PASSWORD"
   )

   MISSING=()

   for var in "${REQUIRED_VARS[@]}"; do
       if [ -z "${!var}" ]; then
           MISSING+=("$var")
       fi
   done

   if [ ${#MISSING[@]} -ne 0 ]; then
       echo "ERROR: Missing required configuration:"
       printf '  - %s\n' "${MISSING[@]}"
       echo ""
       echo "See config-schema.md for required variables"
       exit 1
   fi

   echo "Configuration validation passed"
   ```

---

### Task 2: External Backing Services Configuration
**12-Factor**: IV (Backing Services)
**Priority**: CRITICAL
**Estimated Effort**: 5-7 days
**Agent Team**: Database + Backend agents

#### Implementation Steps

1. **External OrientDB Configuration** (Agent: Database)
   ```java
   // orienteer-core/.../db/DatabaseConnectionFactory.java
   public class DatabaseConnectionFactory {
       private final ApplicationConfig config;
       private ODatabasePool pool;

       public void initialize() {
           String url = config.getOrientdbUrl();

           // Validate URL is not embedded
           if (url.startsWith("plocal:") || url.startsWith("memory:")) {
               if (config.isProductionMode()) {
                   throw new ConfigurationException(
                       "Embedded database not allowed in production. " +
                       "Use remote: connection string."
                   );
               }
               log.warn("Using embedded database - for development only");
           }

           // Create connection pool
           pool = new ODatabasePool(
               url,
               config.getOrientdbUsername(),
               config.getOrientdbPassword()
           );

           pool.setMinPool(config.getOrientdbPoolMin());
           pool.setMaxPool(config.getOrientdbPoolMax());

           // Validate connectivity
           validateConnection();
       }

       private void validateConnection() {
           try (ODatabaseSession db = pool.acquire()) {
               db.query("SELECT FROM OUser LIMIT 1");
               log.info("Database connection validated: " + config.getOrientdbUrl());
           } catch (Exception e) {
               throw new DatabaseException(
                   "Failed to connect to database: " + e.getMessage(), e
               );
           }
       }

       public ODatabaseSession getSession() {
           return pool.acquire();
       }
   }
   ```

2. **Connection Pool with Circuit Breaker** (Agent: Backend)
   ```java
   // orienteer-core/.../db/ResilientDatabaseConnection.java
   public class ResilientDatabaseConnection {
       private final CircuitBreaker circuitBreaker;
       private final DatabaseConnectionFactory factory;

       public ResilientDatabaseConnection(DatabaseConnectionFactory factory) {
           this.factory = factory;

           // Configure circuit breaker
           CircuitBreakerConfig config = CircuitBreakerConfig.custom()
               .failureRateThreshold(50)  // Open if 50% failures
               .waitDurationInOpenState(Duration.ofSeconds(30))
               .ringBufferSizeInHalfOpenState(5)
               .ringBufferSizeInClosedState(10)
               .build();

           this.circuitBreaker = CircuitBreaker.of("orientdb", config);

           // Register event listeners
           circuitBreaker.getEventPublisher()
               .onStateTransition(event -> {
                   log.warn("Circuit breaker state: {} -> {}",
                       event.getStateTransition().getFromState(),
                       event.getStateTransition().getToState());
               });
       }

       public ODatabaseSession getSession() {
           return circuitBreaker.executeSupplier(() -> {
               return factory.getSession();
           });
       }
   }
   ```

3. **Service Health Checks** (Agent: Backend)
   ```java
   // orienteer-core/.../health/BackingServiceHealthCheck.java
   public class BackingServiceHealthCheck {
       public CheckResult checkDatabase() {
           try {
               ODatabaseSession db = connectionFactory.getSession();
               long startTime = System.currentTimeMillis();

               db.query("SELECT FROM OUser LIMIT 1");

               long latency = System.currentTimeMillis() - startTime;

               db.close();

               return CheckResult.healthy()
                   .withDetail("latency_ms", latency)
                   .withDetail("url", config.getOrientdbUrl());
           } catch (Exception e) {
               return CheckResult.unhealthy(
                   "Database connection failed: " + e.getMessage()
               );
           }
       }

       public CheckResult checkRedis() {
           if (!config.getSessionStore().equals("redis")) {
               return CheckResult.healthy("Not configured");
           }

           try {
               Jedis jedis = redisPool.getResource();
               String pong = jedis.ping();
               jedis.close();

               return CheckResult.healthy()
                   .withDetail("response", pong);
           } catch (Exception e) {
               return CheckResult.unhealthy(
                   "Redis connection failed: " + e.getMessage()
               );
           }
       }
   }
   ```

4. **Database Migration Scripts** (Agent: Database)
   ```sql
   -- migrations/V001__external_database_setup.sql
   -- Prepare database for external deployment

   -- Create connection user with limited privileges
   CREATE USER '${ORIENTDB_USERNAME}' IDENTIFIED BY '${ORIENTDB_PASSWORD}';

   -- Grant necessary permissions
   GRANT ALL ON Orienteer TO '${ORIENTDB_USERNAME}';

   -- Create indexes for performance
   CREATE INDEX User.username ON User(username) UNIQUE;
   CREATE INDEX Session.sessionId ON Session(sessionId) UNIQUE;

   -- Configure connection limits
   ALTER DATABASE custom connectionPoolMin=10;
   ALTER DATABASE custom connectionPoolMax=50;
   ```

---

### Task 3: Build, Release, Run Separation
**12-Factor**: V (Build, Release, Run)
**Priority**: HIGH
**Estimated Effort**: 4-6 days
**Agent Team**: DevOps + Backend agents

#### Implementation Steps

1. **Remove Configuration from Build** (Agent: DevOps)
   ```dockerfile
   # Dockerfile - BEFORE
   FROM openjdk:8-jre-slim
   COPY orienteer.properties /app/  # WRONG - config in image
   COPY orienteer.jar /app/
   CMD ["java", "-jar", "/app/orienteer.jar"]

   # Dockerfile - AFTER
   FROM openjdk:8-jre-slim

   # Only application code in image
   COPY orienteer.jar /app/orienteer.jar

   # Configuration via environment
   ENV JAVA_OPTS="-Xmx512m -Xms256m"

   # Validate configuration at startup
   COPY validate-config.sh /app/
   RUN chmod +x /app/validate-config.sh

   ENTRYPOINT ["/app/validate-config.sh"]
   CMD ["java", "$JAVA_OPTS", "-jar", "/app/orienteer.jar"]
   ```

2. **Environment-Specific Configuration** (Agent: DevOps)
   ```yaml
   # k8s/overlays/development/kustomization.yaml
   apiVersion: kustomize.config.k8s.io/v1beta1
   kind: Kustomization

   resources:
   - ../../base

   configMapGenerator:
   - name: orienteer-config
     literals:
     - ORIENTDB_URL=remote:orientdb-dev:2424/Orienteer
     - SERVER_PORT=8080
     - PRODUCTION_MODE=false
     - DEV_MODE=true

   secretGenerator:
   - name: orienteer-secrets
     literals:
     - ORIENTDB_USERNAME=dev_user
     - ORIENTDB_PASSWORD=dev_password
   ```

   ```yaml
   # k8s/overlays/production/kustomization.yaml
   apiVersion: kustomize.config.k8s.io/v1beta1
   kind: Kustomization

   resources:
   - ../../base

   configMapGenerator:
   - name: orienteer-config
     literals:
     - ORIENTDB_URL=remote:orientdb-prod.example.com:2424/Orienteer
     - SERVER_PORT=8080
     - PRODUCTION_MODE=true
     - DEV_MODE=false
     - SESSION_STORE=redis
     - REDIS_URL=redis://redis-cluster:6379

   # Production secrets from external secret manager
   secretGenerator:
   - name: orienteer-secrets
     files:
     - ORIENTDB_USERNAME=secrets/orientdb-username
     - ORIENTDB_PASSWORD=secrets/orientdb-password
   ```

3. **Release Versioning** (Agent: DevOps)
   ```bash
   #!/bin/bash
   # release.sh - Create versioned releases

   VERSION=${1:?Version required}
   BUILD_NUMBER=${2:-$GITHUB_RUN_NUMBER}

   # Build artifact
   mvn clean package -DskipTests

   # Tag image with version
   IMAGE_TAG="${VERSION}-${BUILD_NUMBER}"
   docker build -t orienteer:${IMAGE_TAG} .
   docker tag orienteer:${IMAGE_TAG} orienteer:${VERSION}
   docker tag orienteer:${IMAGE_TAG} orienteer:latest

   # Push to registry
   docker push orienteer:${IMAGE_TAG}
   docker push orienteer:${VERSION}

   # Create release manifest
   cat > release-${VERSION}.yaml <<EOF
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: release-info
   data:
     version: "${VERSION}"
     build: "${BUILD_NUMBER}"
     timestamp: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
     git-commit: "$(git rev-parse HEAD)"
   EOF

   echo "Release ${VERSION} created: orienteer:${IMAGE_TAG}"
   ```

4. **Immutable Releases** (Agent: DevOps)
   ```yaml
   # k8s/base/deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: orienteer
   spec:
     replicas: 2
     strategy:
       type: RollingUpdate
       rollingUpdate:
         maxSurge: 1
         maxUnavailable: 0
     template:
       spec:
         containers:
         - name: orienteer
           image: orienteer:${IMAGE_TAG}  # Immutable tag
           imagePullPolicy: IfNotPresent

           # All configuration from environment
           envFrom:
           - configMapRef:
               name: orienteer-config
           - secretRef:
               name: orienteer-secrets

           # No configuration files mounted
   ```

---

### Task 4: Container Optimization
**12-Factor**: V (Build, Release, Run) + IX (Disposability)
**Priority**: MEDIUM
**Estimated Effort**: 3-4 days
**Agent Team**: DevOps agent

#### Implementation Steps

1. **Multi-Stage Build** (Agent: DevOps)
   ```dockerfile
   # Multi-stage Dockerfile for optimized images

   # Stage 1: Build
   FROM maven:3.8-openjdk-8 AS builder
   WORKDIR /build

   # Copy only POM files first (for layer caching)
   COPY pom.xml .
   COPY */pom.xml ./*/
   RUN mvn dependency:go-offline

   # Copy source and build
   COPY . .
   RUN mvn clean package -DskipTests

   # Stage 2: Runtime
   FROM openjdk:8-jre-alpine
   WORKDIR /app

   # Install required tools
   RUN apk add --no-cache curl bash

   # Copy only artifacts from builder
   COPY --from=builder /build/orienteer-standalone/target/orienteer-*.jar /app/orienteer.jar

   # Copy startup scripts
   COPY docker-entrypoint.sh /app/
   COPY validate-config.sh /app/
   RUN chmod +x /app/*.sh

   # Non-root user
   RUN addgroup -g 1000 orienteer && \
       adduser -D -u 1000 -G orienteer orienteer
   USER orienteer

   # Health check
   HEALTHCHECK --interval=30s --timeout=3s --start-period=60s \
     CMD curl -f http://localhost:8080/health/live || exit 1

   EXPOSE 8080
   ENTRYPOINT ["/app/docker-entrypoint.sh"]
   CMD ["java", "-jar", "/app/orienteer.jar"]
   ```

2. **Startup Optimization** (Agent: Backend)
   ```java
   // orienteer-core/.../startup/OptimizedStartup.java
   public class OptimizedStartup {
       public void start() {
           // Parallel initialization
           ExecutorService executor = Executors.newFixedThreadPool(4);

           List<Future<?>> futures = new ArrayList<>();

           // Initialize database connection
           futures.add(executor.submit(() -> {
               log.info("Initializing database connection");
               databaseFactory.initialize();
           }));

           // Initialize cache
           futures.add(executor.submit(() -> {
               log.info("Initializing cache");
               cacheManager.initialize();
           }));

           // Load modules
           futures.add(executor.submit(() -> {
               log.info("Loading modules");
               moduleManager.loadModules();
           }));

           // Wait for all
           for (Future<?> future : futures) {
               future.get();
           }

           executor.shutdown();

           log.info("Startup complete in {}ms", startupTime);
       }
   }
   ```

---

## Agent Coordination Plan

### Swarm Execution
```javascript
[Single Message - Parallel agent spawning]:
  Task("Configuration Architect", "
    Design configuration schema and externalization strategy.
    Store decisions in memory: swarm/config/*
  ", "system-architect")

  Task("Backend Developer 1", "
    Implement ApplicationConfig and validation.
    Remove embedded configuration.
  ", "backend-dev")

  Task("Database Engineer", "
    External database configuration and migration.
    Connection pooling and circuit breakers.
  ", "backend-dev")

  Task("DevOps Engineer", "
    Docker optimization and release process.
    Kubernetes manifests with Kustomize.
  ", "cicd-engineer")

  Task("Testing Engineer", "
    Test configuration loading across environments.
    Validate backing service connections.
  ", "tester")

  TodoWrite { todos: [
    {content: "Audit all configuration files", status: "pending"},
    {content: "Create ApplicationConfig schema", status: "pending"},
    {content: "Remove embedded configuration", status: "pending"},
    {content: "Create config documentation", status: "pending"},
    {content: "External OrientDB configuration", status: "pending"},
    {content: "Implement circuit breakers", status: "pending"},
    {content: "Add backing service health checks", status: "pending"},
    {content: "Remove config from Docker images", status: "pending"},
    {content: "Create Kustomize overlays", status: "pending"},
    {content: "Implement release versioning", status: "pending"},
    {content: "Optimize container startup", status: "pending"},
    {content: "Write comprehensive tests", status: "pending"}
  ]}
```

---

## Testing Requirements

### Configuration Tests
- Application starts with all config from environment
- Application fails with missing required config
- Same container works in dev/staging/prod
- Configuration validation catches errors

### Backing Service Tests
- Connection to external OrientDB
- Circuit breaker opens on failures
- Health checks reflect service status
- Connection pool sizing correct

### Build/Release Tests
- Docker image has no configuration
- Release tagging works correctly
- Immutable releases can be promoted
- Rollback to previous release works

---

## Success Validation

### Automated Checks
```bash
# No configuration in image
docker run orienteer:latest env | grep -i orientdb
# Should return nothing

# Same image, different environments
docker run -e ORIENTDB_URL=remote:dev:2424 orienteer:latest
docker run -e ORIENTDB_URL=remote:prod:2424 orienteer:latest
# Both should work

# Startup time
time docker run orienteer:latest
# Should be under 60 seconds
```

---

## Deliverables Checklist

- [ ] ApplicationConfig with full validation
- [ ] Zero configuration in properties files
- [ ] External OrientDB connection
- [ ] Connection pool with circuit breakers
- [ ] Backing service health checks
- [ ] Configuration documentation
- [ ] Docker images without configuration
- [ ] Kustomize overlays for environments
- [ ] Release versioning process
- [ ] Container startup under 60s
- [ ] Tests passing in all environments

---

**Next Phase**: [Phase 2 - Stateless Architecture](03-PHASE-2-STATELESS-ARCHITECTURE.md)

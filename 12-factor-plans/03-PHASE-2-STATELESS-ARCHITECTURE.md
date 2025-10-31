# Phase 2: Stateless Architecture Implementation Plan
## Transform to Horizontally Scalable System (8-10 weeks)

**Phase Duration**: 8-10 weeks
**Priority**: CRITICAL
**12-Factor Focus**: VI (Processes), X (Dev/Prod Parity)
**Agent Teams**: 4-5 concurrent teams
**Prerequisites**: Phase 1 complete (external backing services operational)

---

## Phase Objectives

### Primary Goals
1. **Eliminate server-side session state** - Enable horizontal scaling
2. **Implement JWT authentication** - Stateless authentication tokens
3. **External session storage** - Redis-based session management
4. **Remove sticky session requirements** - True load balancing
5. **Session migration utilities** - Zero-downtime transition

### Success Criteria
- ✅ Zero session state stored in application memory
- ✅ Sessions persist in Redis cluster
- ✅ Successfully scale from 2 to 20 instances without session loss
- ✅ Load balancer does not need sticky sessions
- ✅ User sessions survive instance restarts
- ✅ Authentication via JWT tokens

---

## Current State Analysis

### Stateful Components Identified
```java
// orienteer-core/.../web/OrienteerWebSession.java
public class OrienteerWebSession extends WebSession {
    private String username;          // ❌ Server memory
    private ODocument user;            // ❌ Server memory
    private OrienteerWebApplication app;  // ❌ Server memory
    private Locale locale;             // ❌ Server memory

    // Session is serialized to database with server affinity
}

// orienteer-core/.../OrienteerWebApplication.java
// Session data persisted with server binding
```

### Scaling Blockers
1. **Session affinity required** - Users must hit same server
2. **Session loss on scale operations** - Cannot add/remove instances
3. **No failover capability** - Instance failure = session loss
4. **Memory bound** - Sessions consume application memory

---

## Implementation Tasks

### Task 1: JWT Authentication System
**12-Factor**: VI (Processes)
**Priority**: CRITICAL
**Estimated Effort**: 10-12 days
**Agent Team**: Security + Backend agents

#### Implementation Steps

1. **JWT Token Service** (Agent: Security)
   ```java
   // orienteer-core/.../security/JwtTokenService.java
   public class JwtTokenService {
       private final ApplicationConfig config;
       private final SecretKey signingKey;

       public JwtTokenService(ApplicationConfig config) {
           this.config = config;
           // Load signing key from secrets manager
           String keyBase64 = config.getJwtSigningKey();
           this.signingKey = Keys.hmacShaKeyFor(
               Base64.getDecoder().decode(keyBase64)
           );
       }

       /**
        * Generate JWT token for authenticated user
        */
       public String generateToken(ODocument user) {
           Date now = new Date();
           Date expiration = new Date(now.getTime() +
               config.getJwtExpirationMinutes() * 60 * 1000);

           return Jwts.builder()
               .setSubject(user.field("username"))
               .setIssuedAt(now)
               .setExpiration(expiration)
               .claim("userId", user.getIdentity().toString())
               .claim("email", user.field("email"))
               .claim("roles", getUserRoles(user))
               .signWith(signingKey)
               .compact();
       }

       /**
        * Validate and parse JWT token
        */
       public Claims validateToken(String token) {
           try {
               return Jwts.parserBuilder()
                   .setSigningKey(signingKey)
                   .build()
                   .parseClaimsJws(token)
                   .getBody();
           } catch (JwtException e) {
               log.warn("Invalid JWT token: {}", e.getMessage());
               throw new AuthenticationException("Invalid token");
           }
       }

       /**
        * Refresh token (generate new with extended expiration)
        */
       public String refreshToken(String oldToken) {
           Claims claims = validateToken(oldToken);

           // Check if token is close to expiration
           Date expiration = claims.getExpiration();
           long timeToExpiry = expiration.getTime() - System.currentTimeMillis();

           if (timeToExpiry > config.getJwtRefreshThresholdMinutes() * 60 * 1000) {
               return oldToken; // No refresh needed
           }

           // Generate new token with extended expiration
           String userId = claims.get("userId", String.class);
           ODocument user = loadUser(userId);
           return generateToken(user);
       }
   }
   ```

2. **Stateless Authentication Filter** (Agent: Security)
   ```java
   // orienteer-core/.../security/JwtAuthenticationFilter.java
   public class JwtAuthenticationFilter extends OncePerRequestFilter {
       private final JwtTokenService jwtService;

       @Override
       protected void doFilterInternal(
           HttpServletRequest request,
           HttpServletResponse response,
           FilterChain filterChain
       ) throws ServletException, IOException {

           // Extract JWT from Authorization header
           String authHeader = request.getHeader("Authorization");
           if (authHeader != null && authHeader.startsWith("Bearer ")) {
               String token = authHeader.substring(7);

               try {
                   // Validate token
                   Claims claims = jwtService.validateToken(token);

                   // Set user context (thread-local, not session)
                   UserContext.set(new AuthenticatedUser(claims));

                   // Check if token needs refresh
                   String refreshedToken = jwtService.refreshToken(token);
                   if (!refreshedToken.equals(token)) {
                       response.setHeader("X-Token-Refresh", refreshedToken);
                   }

               } catch (AuthenticationException e) {
                   response.setStatus(401);
                   response.getWriter().write("Invalid or expired token");
                   return;
               }
           }

           filterChain.doFilter(request, response);

           // Clear user context after request
           UserContext.clear();
       }
   }
   ```

3. **Thread-Local User Context** (Agent: Backend)
   ```java
   // orienteer-core/.../security/UserContext.java
   public class UserContext {
       private static final ThreadLocal<AuthenticatedUser> context =
           new ThreadLocal<>();

       public static void set(AuthenticatedUser user) {
           context.set(user);
       }

       public static AuthenticatedUser get() {
           AuthenticatedUser user = context.get();
           if (user == null) {
               throw new AuthenticationException("No authenticated user");
           }
           return user;
       }

       public static void clear() {
           context.remove();
       }

       public static boolean isAuthenticated() {
           return context.get() != null;
       }
   }

   // No longer stored in session, only in request thread
   public class AuthenticatedUser {
       private final String userId;
       private final String username;
       private final String email;
       private final List<String> roles;

       // Loaded from JWT claims, not database
       // Valid only for duration of request
   }
   ```

4. **Login Endpoint** (Agent: Backend)
   ```java
   // orienteer-core/.../rest/AuthenticationResource.java
   @Path("/api/auth")
   public class AuthenticationResource {

       @POST
       @Path("/login")
       @Consumes(MediaType.APPLICATION_JSON)
       @Produces(MediaType.APPLICATION_JSON)
       public Response login(LoginRequest request) {
           // Validate credentials against database
           ODocument user = userService.authenticate(
               request.getUsername(),
               request.getPassword()
           );

           if (user == null) {
               return Response.status(401)
                   .entity(new ErrorResponse("Invalid credentials"))
                   .build();
           }

           // Generate JWT token
           String token = jwtService.generateToken(user);

           return Response.ok()
               .entity(new LoginResponse(token, user))
               .build();
       }

       @POST
       @Path("/logout")
       @Produces(MediaType.APPLICATION_JSON)
       public Response logout() {
           // With JWT, logout is client-side (delete token)
           // Optional: Add token to blacklist for immediate revocation
           String token = extractToken();
           if (token != null) {
               tokenBlacklist.add(token);
           }

           return Response.ok()
               .entity(new LogoutResponse("Logged out"))
               .build();
       }

       @POST
       @Path("/refresh")
       @Produces(MediaType.APPLICATION_JSON)
       public Response refresh() {
           String oldToken = extractToken();
           String newToken = jwtService.refreshToken(oldToken);

           return Response.ok()
               .entity(new TokenResponse(newToken))
               .build();
       }
   }
   ```

---

### Task 2: Redis Session Store
**12-Factor**: VI (Processes)
**Priority**: CRITICAL
**Estimated Effort**: 8-10 days
**Agent Team**: Backend + DevOps agents

#### Implementation Steps

1. **Redis Session Manager** (Agent: Backend)
   ```java
   // orienteer-core/.../session/RedisSessionManager.java
   public class RedisSessionManager {
       private final JedisPool redisPool;
       private final ObjectMapper objectMapper;
       private final int sessionTimeoutSeconds;

       public RedisSessionManager(ApplicationConfig config) {
           this.redisPool = new JedisPool(
               config.getRedisUrl()
           );
           this.objectMapper = new ObjectMapper();
           this.sessionTimeoutSeconds =
               config.getSessionTimeoutMinutes() * 60;
       }

       /**
        * Store session data in Redis
        */
       public void saveSession(String sessionId, SessionData data) {
           try (Jedis jedis = redisPool.getResource()) {
               String key = "session:" + sessionId;
               String json = objectMapper.writeValueAsString(data);

               jedis.setex(key, sessionTimeoutSeconds, json);
           } catch (Exception e) {
               log.error("Failed to save session: " + sessionId, e);
               throw new SessionException("Session save failed", e);
           }
       }

       /**
        * Load session data from Redis
        */
       public SessionData loadSession(String sessionId) {
           try (Jedis jedis = redisPool.getResource()) {
               String key = "session:" + sessionId;
               String json = jedis.get(key);

               if (json == null) {
                   return null;  // Session expired or not found
               }

               // Refresh TTL on access
               jedis.expire(key, sessionTimeoutSeconds);

               return objectMapper.readValue(json, SessionData.class);
           } catch (Exception e) {
               log.error("Failed to load session: " + sessionId, e);
               return null;
           }
       }

       /**
        * Delete session from Redis
        */
       public void deleteSession(String sessionId) {
           try (Jedis jedis = redisPool.getResource()) {
               String key = "session:" + sessionId;
               jedis.del(key);
           }
       }

       /**
        * Update session attributes
        */
       public void updateSessionAttribute(
           String sessionId,
           String attribute,
           Object value
       ) {
           SessionData data = loadSession(sessionId);
           if (data == null) {
               data = new SessionData();
           }

           data.setAttribute(attribute, value);
           saveSession(sessionId, data);
       }
   }
   ```

2. **Session Data Model** (Agent: Backend)
   ```java
   // orienteer-core/.../session/SessionData.java
   public class SessionData implements Serializable {
       private String sessionId;
       private Long createdAt;
       private Long lastAccessedAt;
       private String userId;
       private Map<String, Object> attributes;

       // Wicket-specific data (minimal)
       private Locale locale;
       private String pageMapName;

       // No ODocument references - only serializable data
       // No application object references

       public void setAttribute(String key, Object value) {
           if (!isSerializable(value)) {
               throw new IllegalArgumentException(
                   "Value must be serializable: " + key
               );
           }
           attributes.put(key, value);
       }

       private boolean isSerializable(Object value) {
           return value instanceof Serializable;
       }
   }
   ```

3. **Wicket Session Integration** (Agent: Backend)
   ```java
   // orienteer-core/.../web/StatelessOrienteerSession.java
   public class StatelessOrienteerSession extends WebSession {
       private final RedisSessionManager sessionManager;
       private transient SessionData sessionData;

       public StatelessOrienteerSession(Request request) {
           super(request);
           this.sessionManager = getApplication().getSessionManager();
           loadSessionData();
       }

       private void loadSessionData() {
           String sessionId = getId();
           sessionData = sessionManager.loadSession(sessionId);

           if (sessionData == null) {
               // New session
               sessionData = new SessionData();
               sessionData.setSessionId(sessionId);
               sessionData.setCreatedAt(System.currentTimeMillis());
           }

           sessionData.setLastAccessedAt(System.currentTimeMillis());
       }

       @Override
       public void invalidate() {
           sessionManager.deleteSession(getId());
           super.invalidate();
       }

       @Override
       public void dirty() {
           // Save to Redis on every change
           sessionManager.saveSession(getId(), sessionData);
           super.dirty();
       }

       // Replace all server-side state with Redis
       public void setUserAttribute(String key, Object value) {
           sessionData.setAttribute(key, value);
           sessionManager.saveSession(getId(), sessionData);
       }

       public Object getUserAttribute(String key) {
           return sessionData.getAttribute(key);
       }

       // User info from JWT, not session
       public String getUsername() {
           return UserContext.get().getUsername();
       }

       public ODocument getUser() {
           // Load fresh from database each time
           return userService.loadUser(UserContext.get().getUserId());
       }
   }
   ```

4. **Redis Configuration** (Agent: DevOps)
   ```yaml
   # k8s/base/redis-deployment.yaml
   apiVersion: apps/v1
   kind: StatefulSet
   metadata:
     name: redis
   spec:
     serviceName: redis
     replicas: 3  # Redis cluster
     selector:
       matchLabels:
         app: redis
     template:
       metadata:
         labels:
           app: redis
       spec:
         containers:
         - name: redis
           image: redis:6-alpine
           ports:
           - containerPort: 6379
           volumeMounts:
           - name: redis-data
             mountPath: /data
           resources:
             requests:
               memory: "256Mi"
               cpu: "100m"
             limits:
               memory: "512Mi"
               cpu: "200m"
     volumeClaimTemplates:
     - metadata:
         name: redis-data
       spec:
         accessModes: ["ReadWriteOnce"]
         resources:
           requests:
             storage: 10Gi
   ```

---

### Task 3: Session Migration Strategy
**12-Factor**: VI (Processes)
**Priority**: HIGH
**Estimated Effort**: 5-7 days
**Agent Team**: Backend + Database agents

#### Implementation Steps

1. **Dual Session Support** (Agent: Backend)
   ```java
   // orienteer-core/.../session/HybridSessionManager.java
   public class HybridSessionManager {
       private final RedisSessionManager redisManager;
       private final boolean migrationMode;

       public SessionData loadSession(String sessionId) {
           // Try Redis first
           SessionData data = redisManager.loadSession(sessionId);

           if (data == null && migrationMode) {
               // Fall back to database for old sessions
               data = loadFromDatabase(sessionId);

               if (data != null) {
                   // Migrate to Redis
                   log.info("Migrating session to Redis: " + sessionId);
                   redisManager.saveSession(sessionId, data);
               }
           }

           return data;
       }
   }
   ```

2. **Session Migration Script** (Agent: Database)
   ```java
   // orienteer-tools/.../SessionMigrationTool.java
   public class SessionMigrationTool {
       public void migrateAllSessions() {
           log.info("Starting session migration to Redis");

           // Query all active sessions from database
           List<SessionData> sessions = queryActiveSessions();

           log.info("Found {} active sessions to migrate", sessions.size());

           int migrated = 0;
           int failed = 0;

           for (SessionData session : sessions) {
               try {
                   redisManager.saveSession(
                       session.getSessionId(),
                       session
                   );
                   migrated++;

                   if (migrated % 100 == 0) {
                       log.info("Migrated {} sessions", migrated);
                   }
               } catch (Exception e) {
                   log.error("Failed to migrate session: " +
                       session.getSessionId(), e);
                   failed++;
               }
           }

           log.info("Migration complete: {} migrated, {} failed",
               migrated, failed);
       }
   }
   ```

3. **Rolling Deployment Strategy** (Agent: DevOps)
   ```yaml
   # k8s/base/deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: orienteer
   spec:
     replicas: 4
     strategy:
       type: RollingUpdate
       rollingUpdate:
         maxSurge: 2      # 50% more instances during rollout
         maxUnavailable: 0  # Keep all instances running

     template:
       spec:
         containers:
         - name: orienteer
           env:
           - name: SESSION_MIGRATION_MODE
             value: "true"  # Enable during rollout
           - name: SESSION_STORE
             value: "redis"  # New version uses Redis
   ```

---

## Testing Strategy

### Unit Tests (Agent: Testing)
```java
// JwtTokenServiceTest.java
@Test
public void testTokenGeneration() {
    ODocument user = createTestUser();
    String token = jwtService.generateToken(user);
    assertNotNull(token);

    Claims claims = jwtService.validateToken(token);
    assertEquals(user.field("username"), claims.getSubject());
}

// RedisSessionManagerTest.java
@Test
public void testSessionPersistence() {
    SessionData data = new SessionData();
    data.setAttribute("key", "value");

    sessionManager.saveSession("test-123", data);

    SessionData loaded = sessionManager.loadSession("test-123");
    assertEquals("value", loaded.getAttribute("key"));
}
```

### Integration Tests (Agent: Testing)
```java
// StatelessScalingTest.java
@Test
public void testSessionSurvivesInstanceRestart() {
    // Login and get token
    String token = login("testuser", "password");

    // Store data in session
    updateSession(token, "key", "value");

    // Simulate instance restart
    restartInstance();

    // Session should still be accessible
    String value = getSessionValue(token, "key");
    assertEquals("value", value);
}

@Test
public void testScaleFromTwoToTwentyInstances() {
    // Create 100 active sessions
    List<String> tokens = createActiveSessions(100);

    // Scale to 20 instances
    scaleDeployment(20);

    // All sessions should still work
    for (String token : tokens) {
        assertTrue(validateSession(token));
    }
}
```

### Load Tests (Agent: Performance)
```javascript
// k6-load-test.js
import http from 'k6/http';
import { check } from 'k6';

export let options = {
    stages: [
        { duration: '2m', target: 100 },   // Ramp to 100 users
        { duration: '5m', target: 100 },   // Stay at 100
        { duration: '2m', target: 500 },   // Scale to 500
        { duration: '5m', target: 500 },   // Stay at 500
        { duration: '2m', target: 0 },     // Ramp down
    ],
};

export default function() {
    // Login
    let loginRes = http.post('http://orienteer/api/auth/login', {
        username: 'testuser',
        password: 'password'
    });

    let token = loginRes.json('token');

    // Make authenticated requests
    let headers = { 'Authorization': `Bearer ${token}` };

    let res = http.get('http://orienteer/api/data', { headers });

    check(res, {
        'status is 200': (r) => r.status === 200,
        'has valid data': (r) => r.json('data') !== null,
    });
}
```

---

## Agent Coordination Plan

```javascript
[Single Message - Parallel Execution]:
  Task("Security Lead", "
    Design JWT authentication system.
    Implement token service and validation.
  ", "security-manager")

  Task("Backend Developer 1", "
    Implement Redis session manager.
    Integrate with Wicket sessions.
  ", "backend-dev")

  Task("Backend Developer 2", "
    Remove server-side state from OrienteerWebSession.
    Implement thread-local user context.
  ", "backend-dev")

  Task("Database Engineer", "
    Create session migration scripts.
    Support hybrid session mode.
  ", "backend-dev")

  Task("DevOps Engineer", "
    Deploy Redis cluster.
    Configure rolling deployment strategy.
  ", "cicd-engineer")

  Task("Frontend Developer", "
    Update UI to use JWT tokens.
    Implement token refresh logic.
  ", "coder")

  Task("Testing Engineer", "
    Write comprehensive tests.
    Perform load testing.
  ", "tester")

  TodoWrite { todos: [
    {content: "Design JWT authentication", status: "pending"},
    {content: "Implement JwtTokenService", status: "pending"},
    {content: "Create authentication filter", status: "pending"},
    {content: "Implement Redis session manager", status: "pending"},
    {content: "Update Wicket session integration", status: "pending"},
    {content: "Remove server-side state", status: "pending"},
    {content: "Implement thread-local context", status: "pending"},
    {content: "Create session migration tool", status: "pending"},
    {content: "Deploy Redis cluster", status: "pending"},
    {content: "Configure rolling deployment", status: "pending"},
    {content: "Write unit tests", status: "pending"},
    {content: "Perform load testing", status: "pending"}
  ]}
```

---

## Deliverables Checklist

- [ ] JWT token service implemented
- [ ] Stateless authentication filter
- [ ] Thread-local user context
- [ ] Redis session manager
- [ ] Wicket session integration updated
- [ ] All server-side state removed
- [ ] Session migration tool
- [ ] Redis cluster deployed
- [ ] Rolling deployment configured
- [ ] Unit tests: 85%+ coverage
- [ ] Load tests passing (500 concurrent users)
- [ ] Scale test passing (2 to 20 instances)
- [ ] Documentation updated

---

## Success Validation

### Manual Testing
```bash
# Test 1: Login and get JWT
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'
# Should return: {"token": "eyJ..."}

# Test 2: Use JWT for authenticated request
curl http://localhost:8080/api/data \
  -H "Authorization: Bearer eyJ..."
# Should return: 200 OK with data

# Test 3: Scale instances
kubectl scale deployment orienteer --replicas=10
# All sessions should remain active

# Test 4: Restart instance
kubectl delete pod orienteer-xxx
# Sessions should survive
```

---

**Next Phase**: [Phase 3 - Concurrency & Decomposition](04-PHASE-3-CONCURRENCY-DECOMPOSITION.md)

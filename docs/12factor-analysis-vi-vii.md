# 12-Factor App Analysis: Factor VI (Processes) & Factor VII (Port Binding)

## Factor VI: Processes - Execute the app as one or more stateless processes

### Current Implementation Analysis

#### Session Management Implementation
**File: `/orienteer-core/src/main/java/org/orienteer/core/OrienteerWebSession.java`**

**Issues Found:**
1. **Stateful Session Design**: The `OrienteerWebSession` class extends `OrientDbWebSession` and maintains state in session:
   - `perspective` field stores user perspective data
   - Session-bound authentication state
   - User locale preferences stored in session
   - Database connection tied to session lifecycle

```java
public class OrienteerWebSession extends OrientDbWebSession {
    private OIdentifiable perspective;  // Session state

    @Override
    public boolean authenticate(String username, String password) {
        // Stores user state in session
        perspective = null;
        onlineModule.updateSessionUser(getUser(), getId());
    }
}
```

#### Session Clustering with Hazelcast
**File: `/orienteer-core/src/main/java/org/orienteer/core/wicket/pageStore/HazelcastPagesCache.java`**

**Current State:**
- Uses Hazelcast for distributed page caching across cluster
- Session data is replicated but still maintains server affinity
- Wicket pages cached using session+pageId keys

```java
public class HazelcastPagesCache implements SecondLevelPageCache<String, Integer, IManageablePage> {
    private final IMap<String, IManageablePage> cache;
    // Session-based caching with server affinity
}
```

#### OrientDB Data Store Session Persistence
**File: `/orienteer-core/src/main/java/org/orienteer/core/wicket/pageStore/OrientDbDataStore.java`**

**Issues:**
- Session data persisted to OrientDB database
- Creates sticky sessions through database-stored session state
- `isReplicated()` returns `true` but implementation still requires session affinity

### Compliance Assessment: **NON-COMPLIANT**

**Violations:**
1. **Sticky Sessions**: Application maintains user state in web sessions
2. **Session Affinity**: Hazelcast clustering doesn't eliminate need for sticky sessions
3. **Server-Side State**: User perspectives, authentication state stored server-side
4. **Database Session Storage**: Wicket page data stored in OrientDB with session keys

### Recommendations for Factor VI Compliance

1. **Externalize Session State**:
   - Move user perspective data to database or external cache
   - Store authentication tokens instead of session-bound auth state
   - Use stateless JWT tokens for authentication

2. **Eliminate Sticky Sessions**:
   - Redesign to allow any server to handle any request
   - Move page state to client-side or shared storage
   - Use database/Redis for shared state instead of session

3. **Stateless Process Design**:
   - Remove session dependencies from business logic
   - Use request-scoped data only
   - External storage for all persistent state

---

## Factor VII: Port Binding - Export services via port binding

### Current Implementation Analysis

#### Standalone Server Implementation
**File: `/orienteer-standalone/src/main/java/org/orienteer/standalone/ServerRunner.java`**

**Compliance Features:**
✅ **Embedded Jetty Server**: Self-contained with embedded web server
✅ **Configurable Port Binding**: Port configuration through constructor parameters
✅ **HTTP Service Export**: Exports web application via HTTP port

```java
public class ServerRunner {
    public static final int DEFAULT_PORT = 8080;
    private int port = DEFAULT_PORT;
    private String host = null;

    public ServerRunner(String host, int port) {
        this.host = host;
        this.port = port;
    }

    public void start() throws Exception {
        server = new Server();
        ServerConnector http = new ServerConnector(server, new HttpConnectionFactory(httpConfig));
        if(host != null) http.setHost(host);
        http.setPort(port);  // Port binding
        server.addConnector(http);
        server.start();
    }
}
```

#### Startup Configuration
**File: `/orienteer-standalone/src/main/java/org/orienteer/standalone/StartStandalone.java`**

**Features:**
✅ **Command-Line Port Configuration**: `--port=<port>` parameter
✅ **Host Binding Configuration**: `--host=<host>` parameter
✅ **Default Port**: Falls back to 8080 if not specified

```java
public static void main(String[] args) throws Exception {
    int port = ServerRunner.DEFAULT_PORT;
    String portStr = parsedArgs.get(ARG_PORT);
    if(portStr != null) port = Integer.parseInt(portStr);

    String host = parsedArgs.get(ARG_HOST);
    ServerRunner runner = new ServerRunner(host, port);
    runner.start();
}
```

#### Docker Configuration
**File: `/Dockerfile`**

**Features:**
✅ **Port Exposure**: Uses Jetty base image with port configuration
✅ **Environment Variables**: Supports runtime configuration via ENV
✅ **Volume Mounts**: Stateless container design with external volumes

```dockerfile
FROM orienteer/jetty:9.4-jre8
ENV ORIENTEER_HOME="/app"
ENV ORIENTDB_HOME="${ORIENTEER_HOME}/runtime"
ENV JAVA_OPTIONS="-XX:MaxDirectMemorySize=512g $JAVA_OPTIONS -DORIENTEER_HOME=${ORIENTEER_HOME}"
VOLUME ["${ORIENTDB_HOME}", "${MVN_REPOSITORY}"]
```

#### Configuration Properties
**File: `/orienteer-core/src/main/resources/orienteer-default.properties`**

**Features:**
- No hardcoded ports in configuration
- Runtime environment-based configuration
- Property-based host/port binding support

### Compliance Assessment: **FULLY COMPLIANT**

**Compliant Features:**
✅ **Self-Contained Application**: Embedded Jetty server, no external web server required
✅ **Port Binding Export**: Application exports HTTP service via configurable port
✅ **Runtime Port Configuration**: Command-line and environment variable support
✅ **No Hardcoded Ports**: All port configuration is externalized
✅ **Docker Ready**: Container image supports port binding and configuration
✅ **Service Export**: Web application accessible via bound port
✅ **Host Configuration**: Supports binding to specific network interfaces

---

## Summary

### Factor VI (Processes): **NON-COMPLIANT** ❌
- **Major Issues**: Sticky sessions, server-side state management
- **Risk Level**: High - impacts scalability and deployment flexibility
- **Effort Required**: Significant refactoring needed

### Factor VII (Port Binding): **FULLY COMPLIANT** ✅
- **Implementation**: Excellent self-contained design with embedded server
- **Configuration**: Flexible port binding with multiple configuration methods
- **Docker Ready**: Proper containerization support

### Priority Recommendations

1. **High Priority - Factor VI**:
   - Implement stateless session management
   - Move user state to external storage
   - Eliminate session affinity requirements

2. **Maintain - Factor VII**:
   - Current implementation is exemplary
   - Continue using embedded server approach
   - Enhance environment-based configuration

### Risk Assessment

**Factor VI Non-Compliance Risks:**
- Limited horizontal scaling capability
- Load balancer complexity (sticky session requirements)
- Reduced fault tolerance and availability
- Container orchestration difficulties

**Factor VII Compliance Benefits:**
- Easy container deployment
- Service discovery compatibility
- Cloud-native architecture readiness
- Simplified infrastructure requirements
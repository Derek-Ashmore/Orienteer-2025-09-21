# Phase 4: Cloud-Native Features Implementation Plan
## Observability, Resilience, and Production Excellence (8-10 weeks)

**Phase Duration**: 8-10 weeks
**Priority**: HIGH
**12-Factor Focus**: IX (Disposability), XI (Logs), XII (Admin Processes)
**Agent Teams**: 4-6 concurrent teams
**Prerequisites**: Phase 3 complete (process separation operational)

---

## Phase Objectives

### Primary Goals
1. **Distributed tracing** - End-to-end request visibility (Jaeger/Zipkin)
2. **Metrics collection** - Prometheus metrics and Grafana dashboards
3. **Circuit breakers** - Resilience patterns to prevent cascade failures
4. **Advanced logging** - Structured logs with correlation IDs
5. **Service mesh integration** - Istio for traffic management
6. **Chaos engineering** - Validate resilience under failure conditions

### Success Criteria
- ✅ End-to-end request tracing operational
- ✅ Comprehensive metrics dashboard
- ✅ Circuit breakers prevent cascade failures
- ✅ Auto-scaling based on custom metrics
- ✅ 99.99% availability demonstrated (4 nines)
- ✅ Mean Time To Recovery (MTTR) < 5 minutes
- ✅ Chaos tests passing

---

## Implementation Tasks

### Task 1: Distributed Tracing Implementation
**12-Factor**: XI (Logs) + Observability
**Priority**: CRITICAL
**Estimated Effort**: 7-10 days
**Agent Team**: SRE + Backend agents

#### Implementation Steps

1. **Jaeger Infrastructure Deployment** (Agent: SRE)
   ```yaml
   # k8s/observability/jaeger-deployment.yaml
   apiVersion: v1
   kind: Namespace
   metadata:
     name: observability
   ---
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: jaeger
     namespace: observability
   spec:
     replicas: 1
     selector:
       matchLabels:
         app: jaeger
     template:
       metadata:
         labels:
           app: jaeger
       spec:
         containers:
         - name: jaeger
           image: jaegertracing/all-in-one:1.40
           ports:
           - containerPort: 5775
             protocol: UDP
           - containerPort: 6831
             protocol: UDP
           - containerPort: 6832
             protocol: UDP
           - containerPort: 5778
             protocol: TCP
           - containerPort: 16686
             protocol: TCP
           - containerPort: 14268
             protocol: TCP
           env:
           - name: COLLECTOR_ZIPKIN_HOST_PORT
             value: ":9411"
           - name: SPAN_STORAGE_TYPE
             value: "elasticsearch"
           - name: ES_SERVER_URLS
             value: "http://elasticsearch:9200"
           resources:
             requests:
               memory: "512Mi"
               cpu: "250m"
             limits:
               memory: "1Gi"
               cpu: "500m"
   ---
   apiVersion: v1
   kind: Service
   metadata:
     name: jaeger
     namespace: observability
   spec:
     selector:
       app: jaeger
     ports:
     - name: jaeger-collector-http
       port: 14268
       targetPort: 14268
     - name: jaeger-collector-zipkin
       port: 9411
       targetPort: 9411
     - name: jaeger-query
       port: 16686
       targetPort: 16686
     - name: jaeger-agent-thrift
       port: 6831
       protocol: UDP
       targetPort: 6831
   ```

2. **Tracing Library Integration** (Agent: Backend)
   ```java
   // orienteer-core/.../tracing/TracingConfiguration.java
   public class TracingConfiguration {
       private final ApplicationConfig config;

       public Tracer initializeTracer() {
           // Configure Jaeger tracer
           Configuration jaegerConfig = new Configuration(config.getServiceName())
               .withSampler(
                   new Configuration.SamplerConfiguration()
                       .withType("probabilistic")
                       .withParam(config.getTracingSampleRate())
               )
               .withReporter(
                   new Configuration.ReporterConfiguration()
                       .withLogSpans(true)
                       .withSender(
                           new Configuration.SenderConfiguration()
                               .withAgentHost(config.getJaegerAgentHost())
                               .withAgentPort(config.getJaegerAgentPort())
                       )
               );

           // Register tracer globally
           Tracer tracer = jaegerConfig.getTracer();
           GlobalTracer.register(tracer);

           log.info("Distributed tracing initialized: {}",
               config.getServiceName());

           return tracer;
       }
   }
   ```

3. **HTTP Request Tracing Filter** (Agent: Backend)
   ```java
   // orienteer-core/.../tracing/TracingFilter.java
   public class TracingFilter implements Filter {
       private final Tracer tracer;

       @Override
       public void doFilter(ServletRequest request, ServletResponse response,
                          FilterChain chain) throws IOException, ServletException {

           HttpServletRequest httpRequest = (HttpServletRequest) request;

           // Extract trace context from headers (if exists)
           SpanContext parentContext = tracer.extract(
               Format.Builtin.HTTP_HEADERS,
               new HttpServletRequestExtractAdapter(httpRequest)
           );

           // Create new span
           Span span = tracer.buildSpan(httpRequest.getMethod() + " " +
                                        httpRequest.getRequestURI())
               .asChildOf(parentContext)
               .withTag(Tags.SPAN_KIND.getKey(), Tags.SPAN_KIND_SERVER)
               .withTag(Tags.HTTP_METHOD.getKey(), httpRequest.getMethod())
               .withTag(Tags.HTTP_URL.getKey(), httpRequest.getRequestURL().toString())
               .withTag("user.id", UserContext.get().getUserId())
               .start();

           try (Scope scope = tracer.scopeManager().activate(span)) {
               // Add trace ID to MDC for logging
               MDC.put("traceId", span.context().toTraceId());
               MDC.put("spanId", span.context().toSpanId());

               // Continue request processing
               chain.doFilter(request, response);

               // Record response status
               HttpServletResponse httpResponse = (HttpServletResponse) response;
               span.setTag(Tags.HTTP_STATUS.getKey(), httpResponse.getStatus());

               if (httpResponse.getStatus() >= 400) {
                   span.setTag(Tags.ERROR.getKey(), true);
               }

           } catch (Exception e) {
               // Record error
               Tags.ERROR.set(span, true);
               span.log(Map.of(
                   "event", "error",
                   "error.kind", e.getClass().getName(),
                   "message", e.getMessage()
               ));
               throw e;

           } finally {
               span.finish();
               MDC.clear();
           }
       }
   }
   ```

4. **Database Query Tracing** (Agent: Backend)
   ```java
   // orienteer-core/.../tracing/TracedDatabaseConnection.java
   public class TracedDatabaseConnection {
       private final ODatabaseSession database;
       private final Tracer tracer;

       public OResultSet query(String sql, Object... params) {
           Span span = tracer.buildSpan("database.query")
               .withTag(Tags.SPAN_KIND.getKey(), Tags.SPAN_KIND_CLIENT)
               .withTag(Tags.DB_TYPE.getKey(), "orientdb")
               .withTag(Tags.DB_STATEMENT.getKey(), sql)
               .start();

           try (Scope scope = tracer.scopeManager().activate(span)) {
               long startTime = System.currentTimeMillis();

               OResultSet result = database.query(sql, params);

               long duration = System.currentTimeMillis() - startTime;
               span.setTag("db.duration_ms", duration);

               return result;

           } catch (Exception e) {
               Tags.ERROR.set(span, true);
               span.log(Map.of(
                   "event", "error",
                   "message", e.getMessage()
               ));
               throw e;

           } finally {
               span.finish();
           }
       }
   }
   ```

5. **External Service Call Tracing** (Agent: Backend)
   ```java
   // orienteer-core/.../tracing/TracedHttpClient.java
   public class TracedHttpClient {
       private final HttpClient httpClient;
       private final Tracer tracer;

       public HttpResponse get(String url) {
           Span span = tracer.buildSpan("http.request")
               .withTag(Tags.SPAN_KIND.getKey(), Tags.SPAN_KIND_CLIENT)
               .withTag(Tags.HTTP_METHOD.getKey(), "GET")
               .withTag(Tags.HTTP_URL.getKey(), url)
               .start();

           try (Scope scope = tracer.scopeManager().activate(span)) {
               // Inject trace context into outgoing request
               HttpRequest.Builder requestBuilder = HttpRequest.newBuilder()
                   .uri(URI.create(url))
                   .GET();

               tracer.inject(
                   span.context(),
                   Format.Builtin.HTTP_HEADERS,
                   new HttpRequestInjectAdapter(requestBuilder)
               );

               HttpRequest request = requestBuilder.build();
               HttpResponse response = httpClient.send(request,
                   HttpResponse.BodyHandlers.ofString());

               span.setTag(Tags.HTTP_STATUS.getKey(), response.statusCode());

               if (response.statusCode() >= 400) {
                   Tags.ERROR.set(span, true);
               }

               return response;

           } catch (Exception e) {
               Tags.ERROR.set(span, true);
               span.log(Map.of("event", "error", "message", e.getMessage()));
               throw new RuntimeException(e);

           } finally {
               span.finish();
           }
       }
   }
   ```

6. **Queue Message Tracing** (Agent: Backend)
   ```java
   // orienteer-worker/.../tracing/TracedMessageHandler.java
   public abstract class TracedMessageHandler<T> implements MessageHandler<T> {
       private final Tracer tracer;

       @Override
       public void handle(T message) throws Exception {
           // Extract trace context from message headers
           Map<String, String> headers = extractHeaders(message);
           SpanContext parentContext = tracer.extract(
               Format.Builtin.TEXT_MAP,
               new TextMapAdapter(headers)
           );

           // Create span for message processing
           Span span = tracer.buildSpan("queue.process")
               .asChildOf(parentContext)
               .withTag(Tags.SPAN_KIND.getKey(), Tags.SPAN_KIND_CONSUMER)
               .withTag("queue.name", getQueueName())
               .withTag("message.type", message.getClass().getSimpleName())
               .start();

           try (Scope scope = tracer.scopeManager().activate(span)) {
               // Process message
               processMessage(message);

           } catch (Exception e) {
               Tags.ERROR.set(span, true);
               span.log(Map.of("event", "error", "message", e.getMessage()));
               throw e;

           } finally {
               span.finish();
           }
       }

       protected abstract void processMessage(T message) throws Exception;
   }
   ```

---

### Task 2: Metrics Collection and Monitoring
**12-Factor**: XI (Logs) + Observability
**Priority**: CRITICAL
**Estimated Effort**: 7-10 days
**Agent Team**: SRE + Backend agents

#### Implementation Steps

1. **Prometheus Deployment** (Agent: SRE)
   ```yaml
   # k8s/observability/prometheus-deployment.yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: prometheus-config
     namespace: observability
   data:
     prometheus.yml: |
       global:
         scrape_interval: 15s
         evaluation_interval: 15s

       scrape_configs:
       - job_name: 'kubernetes-pods'
         kubernetes_sd_configs:
         - role: pod
         relabel_configs:
         - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
           action: keep
           regex: true
         - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
           action: replace
           target_label: __metrics_path__
           regex: (.+)
         - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
           action: replace
           regex: ([^:]+)(?::\d+)?;(\d+)
           replacement: $1:$2
           target_label: __address__

       - job_name: 'rabbitmq'
         static_configs:
         - targets: ['rabbitmq:15692']

       - job_name: 'redis'
         static_configs:
         - targets: ['redis-exporter:9121']
   ---
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: prometheus
     namespace: observability
   spec:
     replicas: 1
     selector:
       matchLabels:
         app: prometheus
     template:
       metadata:
         labels:
           app: prometheus
       spec:
         containers:
         - name: prometheus
           image: prom/prometheus:v2.40.0
           ports:
           - containerPort: 9090
           volumeMounts:
           - name: config
             mountPath: /etc/prometheus
           - name: data
             mountPath: /prometheus
           args:
           - '--config.file=/etc/prometheus/prometheus.yml'
           - '--storage.tsdb.path=/prometheus'
           - '--storage.tsdb.retention.time=30d'
           resources:
             requests:
               memory: "1Gi"
               cpu: "500m"
             limits:
               memory: "2Gi"
               cpu: "1000m"
         volumes:
         - name: config
           configMap:
             name: prometheus-config
         - name: data
           persistentVolumeClaim:
             claimName: prometheus-data
   ```

2. **Application Metrics** (Agent: Backend)
   ```java
   // orienteer-core/.../metrics/MetricsConfiguration.java
   public class MetricsConfiguration {
       private final MeterRegistry registry;

       public void initialize() {
           // Create Prometheus registry
           PrometheusMeterRegistry prometheusRegistry = new PrometheusMeterRegistry(
               PrometheusConfig.DEFAULT
           );

           // Add common tags
           prometheusRegistry.config().commonTags(
               "service", config.getServiceName(),
               "process_type", config.getProcessType(),
               "version", config.getVersion()
           );

           this.registry = prometheusRegistry;

           // Register JVM metrics
           new ClassLoaderMetrics().bindTo(registry);
           new JvmMemoryMetrics().bindTo(registry);
           new JvmGcMetrics().bindTo(registry);
           new ProcessorMetrics().bindTo(registry);
           new JvmThreadMetrics().bindTo(registry);

           // Register application metrics
           registerApplicationMetrics();

           log.info("Metrics collection initialized");
       }

       private void registerApplicationMetrics() {
           // HTTP request metrics
           Counter.builder("http.requests.total")
               .description("Total HTTP requests")
               .tag("method", "")
               .tag("status", "")
               .register(registry);

           Timer.builder("http.request.duration")
               .description("HTTP request duration")
               .register(registry);

           // Database metrics
           Timer.builder("database.query.duration")
               .description("Database query duration")
               .register(registry);

           // Queue metrics
           Counter.builder("queue.messages.processed")
               .description("Queue messages processed")
               .tag("queue", "")
               .tag("status", "")
               .register(registry);

           // Session metrics
           Gauge.builder("sessions.active", this::getActiveSessions)
               .description("Active user sessions")
               .register(registry);

           // Business metrics
           Counter.builder("reports.generated")
               .description("Reports generated")
               .register(registry);

           Counter.builder("emails.sent")
               .description("Emails sent")
               .tag("status", "")
               .register(registry);
       }

       /**
        * Expose metrics endpoint for Prometheus scraping
        */
       public String scrape() {
           return ((PrometheusMeterRegistry) registry).scrape();
       }
   }
   ```

3. **Metrics Endpoint** (Agent: Backend)
   ```java
   // orienteer-core/.../rest/MetricsResource.java
   @Path("/metrics")
   public class MetricsResource {
       private final MetricsConfiguration metricsConfig;

       /**
        * Prometheus metrics endpoint
        */
       @GET
       @Produces("text/plain; version=0.0.4")
       public Response metrics() {
           String metrics = metricsConfig.scrape();
           return Response.ok(metrics).build();
       }

       /**
        * Health metrics summary (JSON for humans)
        */
       @GET
       @Path("/summary")
       @Produces(MediaType.APPLICATION_JSON)
       public Response summary() {
           MetricsSummary summary = new MetricsSummary();

           // Collect key metrics
           summary.setHttpRequestsTotal(getMetricValue("http.requests.total"));
           summary.setHttpRequestDurationP95(
               getMetricValue("http.request.duration", 0.95)
           );
           summary.setDatabaseQueryDurationP95(
               getMetricValue("database.query.duration", 0.95)
           );
           summary.setActiveSessions(getMetricValue("sessions.active"));
           summary.setQueueDepth(getQueueDepth());

           return Response.ok(summary).build();
       }
   }
   ```

4. **Grafana Dashboards** (Agent: SRE)
   ```json
   // grafana-dashboards/orienteer-overview.json
   {
     "dashboard": {
       "title": "Orienteer Overview",
       "panels": [
         {
           "title": "Request Rate",
           "targets": [
             {
               "expr": "rate(http_requests_total[5m])"
             }
           ]
         },
         {
           "title": "Request Duration (p95)",
           "targets": [
             {
               "expr": "histogram_quantile(0.95, http_request_duration_bucket)"
             }
           ]
         },
         {
           "title": "Error Rate",
           "targets": [
             {
               "expr": "rate(http_requests_total{status=~\"5..\"}[5m])"
             }
           ]
         },
         {
           "title": "Active Sessions",
           "targets": [
             {
               "expr": "sessions_active"
             }
           ]
         },
         {
           "title": "Queue Depth",
           "targets": [
             {
               "expr": "rabbitmq_queue_messages{queue=~\"emails|reports\"}"
             }
           ]
         },
         {
           "title": "Pod Count by Type",
           "targets": [
             {
               "expr": "count(kube_pod_info{pod=~\"orienteer.*\"}) by (process_type)"
             }
           ]
         }
       ]
     }
   }
   ```

5. **Custom Metrics Auto-Scaling** (Agent: SRE)
   ```yaml
   # k8s/base/worker-custom-hpa.yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: orienteer-worker-queue
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: orienteer-worker
     minReplicas: 2
     maxReplicas: 20
     metrics:
     - type: Pods
       pods:
         metric:
           name: queue_messages_per_worker
         target:
           type: AverageValue
           averageValue: "10"  # Scale when >10 messages per worker
     behavior:
       scaleUp:
         stabilizationWindowSeconds: 30
         policies:
         - type: Percent
           value: 100  # Double capacity
           periodSeconds: 30
       scaleDown:
         stabilizationWindowSeconds: 300
         policies:
         - type: Percent
           value: 25  # Reduce by 25%
           periodSeconds: 60
   ```

---

### Task 3: Circuit Breakers and Resilience
**12-Factor**: IX (Disposability) + Resilience
**Priority**: HIGH
**Estimated Effort**: 5-7 days
**Agent Team**: Backend agents

#### Implementation Steps

1. **Circuit Breaker Library** (Agent: Backend)
   ```xml
   <!-- pom.xml -->
   <dependency>
       <groupId>io.github.resilience4j</groupId>
       <artifactId>resilience4j-circuitbreaker</artifactId>
       <version>2.0.2</version>
   </dependency>
   <dependency>
       <groupId>io.github.resilience4j</groupId>
       <artifactId>resilience4j-retry</artifactId>
       <version>2.0.2</version>
   </dependency>
   <dependency>
       <groupId>io.github.resilience4j</groupId>
       <artifactId>resilience4j-bulkhead</artifactId>
       <version>2.0.2</version>
   </dependency>
   ```

2. **Circuit Breaker Configuration** (Agent: Backend)
   ```java
   // orienteer-core/.../resilience/ResilienceConfiguration.java
   public class ResilienceConfiguration {
       private final Map<String, CircuitBreaker> circuitBreakers = new ConcurrentHashMap<>();
       private final Map<String, Retry> retries = new ConcurrentHashMap<>();
       private final Map<String, Bulkhead> bulkheads = new ConcurrentHashMap<>();

       public void initialize() {
           // Create circuit breaker registry
           CircuitBreakerRegistry circuitBreakerRegistry = CircuitBreakerRegistry.of(
               CircuitBreakerConfig.custom()
                   .failureRateThreshold(50)  // 50% failure rate
                   .waitDurationInOpenState(Duration.ofSeconds(30))
                   .permittedNumberOfCallsInHalfOpenState(5)
                   .slidingWindowSize(10)
                   .minimumNumberOfCalls(5)
                   .build()
           );

           // Create retry registry
           RetryRegistry retryRegistry = RetryRegistry.of(
               RetryConfig.custom()
                   .maxAttempts(3)
                   .waitDuration(Duration.ofMillis(500))
                   .retryExceptions(IOException.class, TimeoutException.class)
                   .build()
           );

           // Create bulkhead registry
           BulkheadRegistry bulkheadRegistry = BulkheadRegistry.of(
               BulkheadConfig.custom()
                   .maxConcurrentCalls(25)
                   .maxWaitDuration(Duration.ofMillis(500))
                   .build()
           );

           // Create circuit breakers for external services
           circuitBreakers.put("database",
               circuitBreakerRegistry.circuitBreaker("database"));
           circuitBreakers.put("mail-service",
               circuitBreakerRegistry.circuitBreaker("mail-service"));
           circuitBreakers.put("external-api",
               circuitBreakerRegistry.circuitBreaker("external-api"));

           // Register event listeners
           registerEventListeners();

           log.info("Resilience patterns initialized");
       }

       private void registerEventListeners() {
           circuitBreakers.forEach((name, cb) -> {
               cb.getEventPublisher()
                   .onStateTransition(event -> {
                       log.warn("Circuit breaker [{}] state changed: {} -> {}",
                           name,
                           event.getStateTransition().getFromState(),
                           event.getStateTransition().getToState());

                       // Send alert on state change
                       alertService.sendAlert(
                           "Circuit Breaker State Change",
                           "Service: " + name + ", State: " +
                           event.getStateTransition().getToState()
                       );
                   })
                   .onFailureRateExceeded(event -> {
                       log.error("Circuit breaker [{}] failure rate exceeded: {}%",
                           name, event.getFailureRate());
                   });
           });
       }

       public CircuitBreaker getCircuitBreaker(String name) {
           return circuitBreakers.get(name);
       }

       public Retry getRetry(String name) {
           return retries.computeIfAbsent(name, k ->
               Retry.ofDefaults(name));
       }

       public Bulkhead getBulkhead(String name) {
           return bulkheads.computeIfAbsent(name, k ->
               Bulkhead.ofDefaults(name));
       }
   }
   ```

3. **Resilient Database Access** (Agent: Backend)
   ```java
   // orienteer-core/.../db/ResilientDatabaseAccess.java
   public class ResilientDatabaseAccess {
       private final DatabaseConnectionFactory connectionFactory;
       private final CircuitBreaker circuitBreaker;
       private final Retry retry;
       private final Bulkhead bulkhead;

       public <T> T executeQuery(Supplier<T> querySupplier) {
           // Combine resilience patterns
           Supplier<T> decoratedSupplier = Decorators.ofSupplier(querySupplier)
               .withCircuitBreaker(circuitBreaker)
               .withRetry(retry)
               .withBulkhead(bulkhead)
               .withFallback(
                   Arrays.asList(CallNotPermittedException.class, BulkheadFullException.class),
                   throwable -> {
                       log.error("Database call failed, using fallback", throwable);
                       return getFallbackValue();
                   }
               )
               .decorate();

           return decoratedSupplier.get();
       }

       // Example usage
       public ODocument getUser(String userId) {
           return executeQuery(() -> {
               ODatabaseSession db = connectionFactory.getSession();
               try {
                   return db.query(
                       "SELECT FROM OUser WHERE userId = ?",
                       userId
                   ).next().toElement();
               } finally {
                   db.close();
               }
           });
       }
   }
   ```

4. **Resilient External API Calls** (Agent: Backend)
   ```java
   // orienteer-core/.../external/ResilientApiClient.java
   public class ResilientApiClient {
       private final HttpClient httpClient;
       private final CircuitBreaker circuitBreaker;
       private final Retry retry;
       private final TimeLimiter timeLimiter;

       public CompletableFuture<ApiResponse> callExternalApi(String endpoint) {
           // Create supplier
           Supplier<CompletableFuture<ApiResponse>> futureSupplier = () ->
               CompletableFuture.supplyAsync(() -> {
                   try {
                       HttpRequest request = HttpRequest.newBuilder()
                           .uri(URI.create(endpoint))
                           .timeout(Duration.ofSeconds(5))
                           .build();

                       HttpResponse<String> response = httpClient.send(request,
                           HttpResponse.BodyHandlers.ofString());

                       return new ApiResponse(response.statusCode(), response.body());

                   } catch (Exception e) {
                       throw new RuntimeException(e);
                   }
               });

           // Decorate with resilience patterns
           Supplier<CompletableFuture<ApiResponse>> decoratedSupplier =
               Decorators.ofSupplier(futureSupplier)
                   .withCircuitBreaker(circuitBreaker)
                   .withRetry(retry)
                   .withTimeLimiter(timeLimiter)
                   .decorate();

           return decoratedSupplier.get();
       }
   }
   ```

5. **Circuit Breaker Health Indicator** (Agent: Backend)
   ```java
   // orienteer-core/.../health/CircuitBreakerHealthIndicator.java
   public class CircuitBreakerHealthIndicator {
       private final ResilienceConfiguration resilienceConfig;

       public HealthStatus getHealth() {
           HealthStatus status = new HealthStatus();

           resilienceConfig.getAllCircuitBreakers().forEach((name, cb) -> {
               CircuitBreaker.State state = cb.getState();
               CircuitBreaker.Metrics metrics = cb.getMetrics();

               Map<String, Object> details = new HashMap<>();
               details.put("state", state.toString());
               details.put("failureRate", metrics.getFailureRate());
               details.put("slowCallRate", metrics.getSlowCallRate());
               details.put("bufferedCalls", metrics.getNumberOfBufferedCalls());
               details.put("failedCalls", metrics.getNumberOfFailedCalls());

               if (state == CircuitBreaker.State.OPEN) {
                   status.addCheck(name, CheckResult.unhealthy(
                       "Circuit breaker is OPEN"
                   ).withDetails(details));
               } else {
                   status.addCheck(name, CheckResult.healthy()
                       .withDetails(details));
               }
           });

           return status;
       }
   }
   ```

---

### Task 4: Advanced Logging and Alerting
**12-Factor**: XI (Logs)
**Priority**: MEDIUM
**Estimated Effort**: 5-7 days
**Agent Team**: SRE + Backend agents

#### Implementation Steps

1. **ELK Stack Deployment** (Agent: SRE)
   ```yaml
   # k8s/observability/elasticsearch-deployment.yaml
   apiVersion: apps/v1
   kind: StatefulSet
   metadata:
     name: elasticsearch
     namespace: observability
   spec:
     serviceName: elasticsearch
     replicas: 3
     selector:
       matchLabels:
         app: elasticsearch
     template:
       metadata:
         labels:
           app: elasticsearch
       spec:
         containers:
         - name: elasticsearch
           image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
           ports:
           - containerPort: 9200
             name: http
           - containerPort: 9300
             name: transport
           env:
           - name: cluster.name
             value: "orienteer-logs"
           - name: discovery.seed_hosts
             value: "elasticsearch-0,elasticsearch-1,elasticsearch-2"
           - name: cluster.initial_master_nodes
             value: "elasticsearch-0,elasticsearch-1,elasticsearch-2"
           - name: ES_JAVA_OPTS
             value: "-Xms512m -Xmx512m"
           volumeMounts:
           - name: data
             mountPath: /usr/share/elasticsearch/data
           resources:
             requests:
               memory: "1Gi"
               cpu: "500m"
             limits:
               memory: "2Gi"
               cpu: "1000m"
     volumeClaimTemplates:
     - metadata:
         name: data
       spec:
         accessModes: ["ReadWriteOnce"]
         resources:
           requests:
             storage: 50Gi
   ```

2. **Fluentd Log Collector** (Agent: SRE)
   ```yaml
   # k8s/observability/fluentd-daemonset.yaml
   apiVersion: apps/v1
   kind: DaemonSet
   metadata:
     name: fluentd
     namespace: observability
   spec:
     selector:
       matchLabels:
         app: fluentd
     template:
       metadata:
         labels:
           app: fluentd
       spec:
         containers:
         - name: fluentd
           image: fluent/fluentd-kubernetes-daemonset:v1-debian-elasticsearch
           env:
           - name: FLUENT_ELASTICSEARCH_HOST
             value: "elasticsearch"
           - name: FLUENT_ELASTICSEARCH_PORT
             value: "9200"
           volumeMounts:
           - name: varlog
             mountPath: /var/log
           - name: varlibdockercontainers
             mountPath: /var/lib/docker/containers
             readOnly: true
           resources:
             requests:
               memory: "200Mi"
               cpu: "100m"
             limits:
               memory: "500Mi"
               cpu: "200m"
         volumes:
         - name: varlog
           hostPath:
             path: /var/log
         - name: varlibdockercontainers
           hostPath:
             path: /var/lib/docker/containers
   ```

3. **Alert Manager Configuration** (Agent: SRE)
   ```yaml
   # k8s/observability/alertmanager-config.yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: alertmanager-config
     namespace: observability
   data:
     alertmanager.yml: |
       global:
         resolve_timeout: 5m

       route:
         receiver: 'slack'
         group_by: ['alertname', 'cluster', 'service']
         group_wait: 10s
         group_interval: 10s
         repeat_interval: 12h

       receivers:
       - name: 'slack'
         slack_configs:
         - api_url: 'SLACK_WEBHOOK_URL'
           channel: '#alerts'
           title: 'Orienteer Alert'
           text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
   ```

4. **Prometheus Alert Rules** (Agent: SRE)
   ```yaml
   # prometheus-alerts.yaml
   groups:
   - name: orienteer
     interval: 30s
     rules:
     - alert: HighErrorRate
       expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
       for: 5m
       labels:
         severity: critical
       annotations:
         summary: High error rate detected
         description: Error rate is {{ $value }} requests/second

     - alert: HighLatency
       expr: histogram_quantile(0.95, http_request_duration_bucket) > 1
       for: 5m
       labels:
         severity: warning
       annotations:
         summary: High latency detected
         description: P95 latency is {{ $value }} seconds

     - alert: CircuitBreakerOpen
       expr: circuit_breaker_state{state="open"} == 1
       for: 1m
       labels:
         severity: critical
       annotations:
         summary: Circuit breaker is open
         description: Circuit breaker {{ $labels.name }} is open

     - alert: QueueDepthHigh
       expr: rabbitmq_queue_messages > 1000
       for: 10m
       labels:
         severity: warning
       annotations:
         summary: High queue depth
         description: Queue {{ $labels.queue }} has {{ $value }} messages
   ```

---

### Task 5: Chaos Engineering
**12-Factor**: IX (Disposability) + Resilience Validation
**Priority**: MEDIUM
**Estimated Effort**: 5-7 days
**Agent Team**: SRE + Testing agents

#### Implementation Steps

1. **Chaos Mesh Deployment** (Agent: SRE)
   ```bash
   # Install Chaos Mesh
   kubectl create ns chaos-testing
   helm repo add chaos-mesh https://charts.chaos-mesh.org
   helm install chaos-mesh chaos-mesh/chaos-mesh \
     --namespace=chaos-testing \
     --set chaosDaemon.runtime=containerd \
     --set chaosDaemon.socketPath=/run/containerd/containerd.sock
   ```

2. **Pod Failure Test** (Agent: SRE)
   ```yaml
   # chaos-tests/pod-failure.yaml
   apiVersion: chaos-mesh.org/v1alpha1
   kind: PodChaos
   metadata:
     name: pod-failure-test
     namespace: chaos-testing
   spec:
     action: pod-failure
     mode: one
     selector:
       namespaces:
         - default
       labelSelectors:
         app: orienteer
         process-type: web
     duration: "30s"
     scheduler:
       cron: "@every 1h"
   ```

3. **Network Latency Test** (Agent: SRE)
   ```yaml
   # chaos-tests/network-delay.yaml
   apiVersion: chaos-mesh.org/v1alpha1
   kind: NetworkChaos
   metadata:
     name: network-delay-test
     namespace: chaos-testing
   spec:
     action: delay
     mode: all
     selector:
       namespaces:
         - default
       labelSelectors:
         app: orienteer
     delay:
       latency: "100ms"
       correlation: "100"
       jitter: "50ms"
     duration: "5m"
   ```

4. **Chaos Test Suite** (Agent: Testing)
   ```java
   // orienteer-tests/.../chaos/ChaosTestSuite.java
   public class ChaosTestSuite {
       private final KubernetesClient k8sClient;
       private final TestMetrics metrics;

       /**
        * Test: Application survives random pod failures
        */
       @Test
       public void testPodFailureResilience() {
           // Record baseline metrics
           metrics.recordBaseline();

           // Inject chaos: Kill random pods
           injectChaos("pod-failure-test");

           // Wait for recovery
           await().atMost(2, MINUTES).until(() ->
               allPodsHealthy()
           );

           // Verify metrics
           assertThat(metrics.getErrorRate())
               .isLessThan(0.01);  // < 1% error rate
           assertThat(metrics.getP95Latency())
               .isLessThan(1000);  // < 1 second

           // Verify no data loss
           assertThat(getActiveSessionCount())
               .isGreaterThan(0);
       }

       /**
        * Test: Application handles network delays gracefully
        */
       @Test
       public void testNetworkDelayResilience() {
           metrics.recordBaseline();

           // Inject network delay
           injectChaos("network-delay-test");

           // Verify circuit breakers activate
           await().atMost(1, MINUTES).until(() ->
               circuitBreakerStateIs("database", CircuitBreaker.State.OPEN)
           );

           // Verify fallback mechanisms
           ApiResponse response = callApi("/api/users");
           assertThat(response.getStatus()).isEqualTo(200);
           assertThat(response.isFromCache()).isTrue();

           // Remove chaos
           removeChaos("network-delay-test");

           // Verify recovery
           await().atMost(1, MINUTES).until(() ->
               circuitBreakerStateIs("database", CircuitBreaker.State.CLOSED)
           );
       }
   }
   ```

---

## Agent Coordination Plan

```javascript
[Single Message - Parallel Execution]:
  Task("SRE Lead", "
    Deploy observability stack (Jaeger, Prometheus, Grafana, ELK).
    Configure monitoring and alerting.
  ", "sre")

  Task("Backend Developer 1", "
    Implement distributed tracing.
    Add tracing to all service calls.
  ", "backend-dev")

  Task("Backend Developer 2", "
    Implement metrics collection.
    Add application and business metrics.
  ", "backend-dev")

  Task("Backend Developer 3", "
    Implement circuit breakers.
    Add resilience patterns to external calls.
  ", "backend-dev")

  Task("SRE Engineer", "
    Set up Chaos Mesh.
    Create chaos test scenarios.
  ", "sre")

  Task("Testing Engineer", "
    Write chaos test suite.
    Validate resilience under failure.
  ", "tester")

  Task("Documentation", "
    Create runbooks and playbooks.
    Document alerting and incident response.
  ", "reviewer")

  TodoWrite { todos: [
    {content: "Deploy Jaeger tracing", status: "pending"},
    {content: "Implement tracing library", status: "pending"},
    {content: "Add HTTP request tracing", status: "pending"},
    {content: "Add database query tracing", status: "pending"},
    {content: "Add queue message tracing", status: "pending"},
    {content: "Deploy Prometheus", status: "pending"},
    {content: "Implement metrics collection", status: "pending"},
    {content: "Create Grafana dashboards", status: "pending"},
    {content: "Configure auto-scaling on custom metrics", status: "pending"},
    {content: "Implement circuit breakers", status: "pending"},
    {content: "Add retry and bulkhead patterns", status: "pending"},
    {content: "Deploy ELK stack", status: "pending"},
    {content: "Configure alert manager", status: "pending"},
    {content: "Deploy Chaos Mesh", status: "pending"},
    {content: "Create chaos test scenarios", status: "pending"},
    {content: "Write comprehensive tests", status: "pending"}
  ]}
```

---

## Deliverables Checklist

- [ ] Jaeger distributed tracing deployed
- [ ] Tracing instrumentation complete
- [ ] Prometheus metrics collection
- [ ] Grafana dashboards created
- [ ] Custom metrics auto-scaling
- [ ] Circuit breakers implemented
- [ ] Retry and bulkhead patterns
- [ ] ELK stack for log aggregation
- [ ] Alert manager configured
- [ ] Prometheus alert rules
- [ ] Chaos Mesh deployed
- [ ] Chaos test scenarios created
- [ ] Chaos tests passing
- [ ] Runbooks and playbooks
- [ ] Documentation complete

---

## Success Validation

### Automated Checks
```bash
# Verify tracing
curl http://jaeger:16686/api/traces?service=orienteer-web

# Verify metrics
curl http://prometheus:9090/api/v1/query?query=http_requests_total

# Verify circuit breakers
curl http://localhost:8080/health | jq .circuitBreakers

# Run chaos tests
kubectl apply -f chaos-tests/pod-failure.yaml
# Verify application continues serving traffic
```

### Manual Validation
- [ ] End-to-end traces visible in Jaeger
- [ ] Grafana dashboards showing real-time data
- [ ] Circuit breakers activate under load
- [ ] Alerts triggered and received
- [ ] Application survives pod failures
- [ ] Application handles network delays
- [ ] MTTR < 5 minutes

---

**Next Phase**: [Phase 5 - Production Hardening](06-PHASE-5-PRODUCTION-HARDENING.md)

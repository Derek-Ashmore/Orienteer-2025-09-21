# Phase 3: Concurrency & Decomposition Implementation Plan
## Process Separation and Independent Scaling (8-10 weeks)

**Phase Duration**: 8-10 weeks
**Priority**: HIGH
**12-Factor Focus**: VIII (Concurrency)
**Agent Teams**: 4-5 concurrent teams
**Prerequisites**: Phase 2 complete (stateless architecture operational)

---

## Phase Objectives

### Primary Goals
1. **Separate web and worker processes** - Independent scaling by workload type
2. **Implement message queue** - Async job processing (RabbitMQ/SQS)
3. **Background job framework** - Scheduled and async tasks
4. **Process-type specific scaling** - Scale web/workers independently
5. **Zero blocking web requests** - All long operations async

### Success Criteria
- ✅ Web and worker processes run separately
- ✅ Queue-based async processing operational
- ✅ Zero blocking operations in web requests (all < 200ms)
- ✅ Web processes scale independently from workers
- ✅ Background jobs processed reliably
- ✅ Queue depth monitoring and auto-scaling

---

## Current State Analysis

### Monolithic Process Model
```java
// Current: Everything runs in single JVM process
OrienteerApplication {
    - Web request handling
    - Background tasks
    - Scheduled jobs
    - Admin operations
    - Email sending
    - Report generation
    - Data imports/exports
    - Batch processing
}
// Problem: Cannot scale different workloads independently
```

### Blocking Operations Identified
```java
// orienteer-mail: Blocks web thread while sending email
public void sendEmail(EmailMessage message) {
    mailService.send(message);  // ❌ Blocks for 2-5 seconds
}

// orienteer-bpm: Long-running workflow executions
public void executeWorkflow(Workflow workflow) {
    workflow.execute();  // ❌ Blocks for minutes
}

// orienteer-birt: Report generation blocks request
public byte[] generateReport(ReportParams params) {
    return reportEngine.generate(params);  // ❌ Blocks for 30+ seconds
}

// orienteer-etl: Data imports block web thread
public void importData(DataSource source) {
    etlProcessor.process(source);  // ❌ Blocks for hours
}
```

---

## Implementation Tasks

### Task 1: Message Queue Infrastructure
**12-Factor**: VIII (Concurrency)
**Priority**: CRITICAL
**Estimated Effort**: 5-7 days
**Agent Team**: DevOps + Backend agents

#### Implementation Steps

1. **Queue Service Selection and Deployment** (Agent: DevOps)
   ```yaml
   # k8s/base/rabbitmq-deployment.yaml
   apiVersion: apps/v1
   kind: StatefulSet
   metadata:
     name: rabbitmq
   spec:
     serviceName: rabbitmq
     replicas: 3
     selector:
       matchLabels:
         app: rabbitmq
     template:
       metadata:
         labels:
           app: rabbitmq
       spec:
         containers:
         - name: rabbitmq
           image: rabbitmq:3.11-management
           ports:
           - containerPort: 5672
             name: amqp
           - containerPort: 15672
             name: management
           env:
           - name: RABBITMQ_DEFAULT_USER
             valueFrom:
               secretKeyRef:
                 name: rabbitmq-credentials
                 key: username
           - name: RABBITMQ_DEFAULT_PASS
             valueFrom:
               secretKeyRef:
                 name: rabbitmq-credentials
                 key: password
           - name: RABBITMQ_ERLANG_COOKIE
             valueFrom:
               secretKeyRef:
                 name: rabbitmq-credentials
                 key: erlang-cookie
           volumeMounts:
           - name: rabbitmq-data
             mountPath: /var/lib/rabbitmq
           resources:
             requests:
               memory: "512Mi"
               cpu: "250m"
             limits:
               memory: "1Gi"
               cpu: "500m"
     volumeClaimTemplates:
     - metadata:
         name: rabbitmq-data
       spec:
         accessModes: ["ReadWriteOnce"]
         resources:
           requests:
             storage: 20Gi
   ---
   apiVersion: v1
   kind: Service
   metadata:
     name: rabbitmq
   spec:
     selector:
       app: rabbitmq
     ports:
     - port: 5672
       name: amqp
     - port: 15672
       name: management
   ```

2. **Queue Connection Manager** (Agent: Backend)
   ```java
   // orienteer-core/.../queue/QueueConnectionFactory.java
   public class QueueConnectionFactory {
       private final ApplicationConfig config;
       private ConnectionFactory connectionFactory;
       private Connection connection;
       private final Map<String, Channel> channelPool = new ConcurrentHashMap<>();

       public void initialize() {
           connectionFactory = new ConnectionFactory();
           connectionFactory.setHost(config.getQueueHost());
           connectionFactory.setPort(config.getQueuePort());
           connectionFactory.setUsername(config.getQueueUsername());
           connectionFactory.setPassword(config.getQueuePassword());

           // Connection settings for reliability
           connectionFactory.setAutomaticRecoveryEnabled(true);
           connectionFactory.setNetworkRecoveryInterval(10000);
           connectionFactory.setRequestedHeartbeat(60);
           connectionFactory.setConnectionTimeout(30000);

           try {
               connection = connectionFactory.newConnection("orienteer-app");
               log.info("Connected to message queue: {}:{}",
                   config.getQueueHost(), config.getQueuePort());

               // Declare queues
               declareQueues();

           } catch (Exception e) {
               throw new QueueException("Failed to connect to message queue", e);
           }
       }

       private void declareQueues() throws IOException {
           Channel channel = connection.createChannel();

           // Email queue
           channel.queueDeclare("emails", true, false, false, null);

           // Report generation queue
           channel.queueDeclare("reports", true, false, false, null);

           // Data processing queue
           channel.queueDeclare("data-processing", true, false, false, null);

           // Workflow execution queue
           channel.queueDeclare("workflows", true, false, false, null);

           // Dead letter queue for failed messages
           channel.queueDeclare("dead-letter", true, false, false, null);

           channel.close();
       }

       public Channel getChannel(String queueName) {
           return channelPool.computeIfAbsent(queueName, k -> {
               try {
                   return connection.createChannel();
               } catch (IOException e) {
                   throw new QueueException("Failed to create channel", e);
               }
           });
       }
   }
   ```

3. **Message Publisher** (Agent: Backend)
   ```java
   // orienteer-core/.../queue/MessagePublisher.java
   public class MessagePublisher {
       private final QueueConnectionFactory queueFactory;
       private final ObjectMapper objectMapper;

       /**
        * Publish message to queue
        */
       public void publish(String queueName, Object message) {
           try {
               Channel channel = queueFactory.getChannel(queueName);

               // Serialize message to JSON
               String json = objectMapper.writeValueAsString(message);
               byte[] body = json.getBytes(StandardCharsets.UTF_8);

               // Publish with persistent delivery mode
               AMQP.BasicProperties props = new AMQP.BasicProperties.Builder()
                   .deliveryMode(2)  // Persistent
                   .contentType("application/json")
                   .timestamp(new Date())
                   .messageId(UUID.randomUUID().toString())
                   .build();

               channel.basicPublish("", queueName, props, body);

               log.debug("Published message to queue {}: {}", queueName, message);

           } catch (Exception e) {
               log.error("Failed to publish message to queue: " + queueName, e);
               throw new QueueException("Failed to publish message", e);
           }
       }

       /**
        * Publish with delay (scheduled execution)
        */
       public void publishDelayed(String queueName, Object message, long delayMs) {
           // Use RabbitMQ delayed message plugin or implement with TTL
           Map<String, Object> headers = new HashMap<>();
           headers.put("x-delay", delayMs);

           try {
               Channel channel = queueFactory.getChannel(queueName);
               String json = objectMapper.writeValueAsString(message);

               AMQP.BasicProperties props = new AMQP.BasicProperties.Builder()
                   .deliveryMode(2)
                   .contentType("application/json")
                   .headers(headers)
                   .build();

               channel.basicPublish("delayed-exchange", queueName, props,
                   json.getBytes(StandardCharsets.UTF_8));

           } catch (Exception e) {
               throw new QueueException("Failed to publish delayed message", e);
           }
       }
   }
   ```

---

### Task 2: Worker Process Implementation
**12-Factor**: VIII (Concurrency)
**Priority**: CRITICAL
**Estimated Effort**: 10-14 days
**Agent Team**: Backend agents (2-3)

#### Implementation Steps

1. **Worker Process Base** (Agent: Backend)
   ```java
   // orienteer-worker/.../WorkerApplication.java
   public class WorkerApplication {
       private final QueueConnectionFactory queueFactory;
       private final List<MessageHandler> handlers;
       private final ExecutorService executorService;
       private volatile boolean running = true;

       public static void main(String[] args) {
           WorkerApplication app = new WorkerApplication();
           app.start();
       }

       public void start() {
           log.info("Starting Orienteer Worker Process");

           // Initialize dependencies
           ApplicationConfig config = ApplicationConfig.load();
           queueFactory = new QueueConnectionFactory(config);
           queueFactory.initialize();

           // Register graceful shutdown
           registerShutdownHook();

           // Create thread pool for message processing
           int workerThreads = config.getWorkerThreads();
           executorService = Executors.newFixedThreadPool(workerThreads);

           // Initialize message handlers
           initializeHandlers();

           // Start consuming from queues
           startConsuming();

           log.info("Worker process started with {} threads", workerThreads);
       }

       private void initializeHandlers() {
           handlers = Arrays.asList(
               new EmailMessageHandler(),
               new ReportGenerationHandler(),
               new DataProcessingHandler(),
               new WorkflowExecutionHandler()
           );
       }

       private void startConsuming() {
           for (MessageHandler handler : handlers) {
               String queueName = handler.getQueueName();
               Channel channel = queueFactory.getChannel(queueName);

               try {
                   // Set prefetch count to limit concurrent messages
                   channel.basicQos(handler.getConcurrencyLimit());

                   // Create consumer
                   DeliverCallback deliverCallback = (consumerTag, delivery) -> {
                       executorService.submit(() -> {
                           processMessage(handler, delivery);
                       });
                   };

                   channel.basicConsume(queueName, false, deliverCallback,
                       consumerTag -> {});

                   log.info("Started consuming from queue: {}", queueName);

               } catch (IOException e) {
                   log.error("Failed to start consuming from queue: " + queueName, e);
               }
           }
       }

       private void processMessage(MessageHandler handler, Delivery delivery) {
           String messageId = delivery.getProperties().getMessageId();
           String queueName = handler.getQueueName();

           try {
               log.debug("Processing message {} from queue {}", messageId, queueName);

               // Deserialize message
               String json = new String(delivery.getBody(), StandardCharsets.UTF_8);
               Object message = handler.deserialize(json);

               // Process message
               handler.handle(message);

               // Acknowledge successful processing
               Channel channel = queueFactory.getChannel(queueName);
               channel.basicAck(delivery.getEnvelope().getDeliveryTag(), false);

               log.debug("Successfully processed message {}", messageId);

           } catch (Exception e) {
               log.error("Failed to process message " + messageId, e);
               handleFailedMessage(handler, delivery, e);
           }
       }

       private void handleFailedMessage(MessageHandler handler, Delivery delivery,
                                       Exception error) {
           try {
               Channel channel = queueFactory.getChannel(handler.getQueueName());

               // Check retry count
               Integer retryCount = getRetryCount(delivery.getProperties());

               if (retryCount < handler.getMaxRetries()) {
                   // Requeue with incremented retry count
                   retryCount++;
                   log.warn("Requeueing message (retry {}/{})",
                       retryCount, handler.getMaxRetries());

                   Map<String, Object> headers = new HashMap<>();
                   headers.put("x-retry-count", retryCount);

                   AMQP.BasicProperties props = delivery.getProperties().builder()
                       .headers(headers)
                       .build();

                   channel.basicPublish("", handler.getQueueName(), props,
                       delivery.getBody());

                   channel.basicAck(delivery.getEnvelope().getDeliveryTag(), false);

               } else {
                   // Max retries exceeded, send to dead letter queue
                   log.error("Max retries exceeded, moving to dead letter queue");

                   channel.basicPublish("", "dead-letter", null, delivery.getBody());
                   channel.basicAck(delivery.getEnvelope().getDeliveryTag(), false);
               }

           } catch (IOException e) {
               log.error("Failed to handle failed message", e);
           }
       }

       private void registerShutdownHook() {
           Runtime.getRuntime().addShutdownHook(new Thread(() -> {
               log.info("Shutdown signal received, stopping worker process");
               running = false;

               // Stop processing new messages
               executorService.shutdown();

               try {
                   // Wait for current messages to complete
                   if (!executorService.awaitTermination(30, TimeUnit.SECONDS)) {
                       executorService.shutdownNow();
                   }
               } catch (InterruptedException e) {
                   executorService.shutdownNow();
               }

               log.info("Worker process stopped");
           }));
       }
   }
   ```

2. **Message Handler Interface** (Agent: Backend)
   ```java
   // orienteer-worker/.../MessageHandler.java
   public interface MessageHandler<T> {
       /**
        * Queue name to consume from
        */
       String getQueueName();

       /**
        * Maximum concurrent messages to process
        */
       int getConcurrencyLimit();

       /**
        * Maximum retry attempts
        */
       int getMaxRetries();

       /**
        * Deserialize message from JSON
        */
       T deserialize(String json) throws IOException;

       /**
        * Process the message
        */
       void handle(T message) throws Exception;
   }
   ```

3. **Email Message Handler** (Agent: Backend)
   ```java
   // orienteer-worker/.../handlers/EmailMessageHandler.java
   public class EmailMessageHandler implements MessageHandler<EmailMessage> {
       private final MailService mailService;
       private final ObjectMapper objectMapper;

       @Override
       public String getQueueName() {
           return "emails";
       }

       @Override
       public int getConcurrencyLimit() {
           return 10;  // Process 10 emails concurrently
       }

       @Override
       public int getMaxRetries() {
           return 3;
       }

       @Override
       public EmailMessage deserialize(String json) throws IOException {
           return objectMapper.readValue(json, EmailMessage.class);
       }

       @Override
       public void handle(EmailMessage message) throws Exception {
           log.info("Sending email to: {}", message.getTo());

           // Send email (blocking operation, but in worker process)
           mailService.send(message);

           log.info("Email sent successfully to: {}", message.getTo());
       }
   }

   // Email message model
   public class EmailMessage implements Serializable {
       private String to;
       private String subject;
       private String body;
       private List<String> attachments;
       private Map<String, String> headers;

       // Getters and setters
   }
   ```

4. **Report Generation Handler** (Agent: Backend)
   ```java
   // orienteer-worker/.../handlers/ReportGenerationHandler.java
   public class ReportGenerationHandler implements MessageHandler<ReportRequest> {
       private final ReportEngine reportEngine;
       private final StorageService storageService;

       @Override
       public String getQueueName() {
           return "reports";
       }

       @Override
       public int getConcurrencyLimit() {
           return 5;  // CPU-intensive, limit concurrency
       }

       @Override
       public int getMaxRetries() {
           return 2;
       }

       @Override
       public ReportRequest deserialize(String json) throws IOException {
           return objectMapper.readValue(json, ReportRequest.class);
       }

       @Override
       public void handle(ReportRequest request) throws Exception {
           log.info("Generating report: {}", request.getReportId());

           // Generate report (CPU-intensive, long-running)
           byte[] reportData = reportEngine.generate(request.getParams());

           // Store report in cloud storage
           String reportUrl = storageService.store(
               "reports/" + request.getReportId() + ".pdf",
               reportData
           );

           // Update database with report URL
           updateReportStatus(request.getReportId(), reportUrl);

           // Optionally notify user
           notifyUserReportReady(request.getUserId(), reportUrl);

           log.info("Report generated: {}", reportUrl);
       }
   }
   ```

5. **Data Processing Handler** (Agent: Backend)
   ```java
   // orienteer-worker/.../handlers/DataProcessingHandler.java
   public class DataProcessingHandler implements MessageHandler<DataProcessingJob> {
       private final ETLProcessor etlProcessor;

       @Override
       public String getQueueName() {
           return "data-processing";
       }

       @Override
       public int getConcurrencyLimit() {
           return 2;  // Memory-intensive, low concurrency
       }

       @Override
       public int getMaxRetries() {
           return 1;
       }

       @Override
       public DataProcessingJob deserialize(String json) throws IOException {
           return objectMapper.readValue(json, DataProcessingJob.class);
       }

       @Override
       public void handle(DataProcessingJob job) throws Exception {
           log.info("Processing data job: {}", job.getJobId());

           // Process large dataset (memory and CPU intensive)
           ProcessingResult result = etlProcessor.process(job);

           // Update job status
           updateJobStatus(job.getJobId(), result);

           log.info("Data processing complete: {}", job.getJobId());
       }
   }
   ```

---

### Task 3: Convert Web Endpoints to Async
**12-Factor**: VIII (Concurrency)
**Priority**: HIGH
**Estimated Effort**: 7-10 days
**Agent Team**: Backend agents (2-3)

#### Implementation Steps

1. **Async Email Endpoint** (Agent: Backend)
   ```java
   // orienteer-core/.../rest/EmailResource.java
   @Path("/api/emails")
   public class EmailResource {
       private final MessagePublisher messagePublisher;

       /**
        * Send email asynchronously
        * Returns immediately with job ID
        */
       @POST
       @Consumes(MediaType.APPLICATION_JSON)
       @Produces(MediaType.APPLICATION_JSON)
       public Response sendEmail(EmailRequest request) {
           // Validate request
           validateEmailRequest(request);

           // Create message
           EmailMessage message = new EmailMessage();
           message.setTo(request.getTo());
           message.setSubject(request.getSubject());
           message.setBody(request.getBody());

           // Generate job ID
           String jobId = UUID.randomUUID().toString();
           message.setJobId(jobId);

           // Publish to queue (returns immediately)
           messagePublisher.publish("emails", message);

           // Return job ID for tracking
           return Response.accepted()
               .entity(new JobResponse(jobId, "Email queued for sending"))
               .build();
       }

       /**
        * Check email send status
        */
       @GET
       @Path("/{jobId}/status")
       @Produces(MediaType.APPLICATION_JSON)
       public Response getEmailStatus(@PathParam("jobId") String jobId) {
           JobStatus status = jobStatusService.getStatus(jobId);

           return Response.ok(status).build();
       }
   }
   ```

2. **Async Report Generation** (Agent: Backend)
   ```java
   // orienteer-core/.../rest/ReportResource.java
   @Path("/api/reports")
   public class ReportResource {
       private final MessagePublisher messagePublisher;

       /**
        * Generate report asynchronously
        * OLD: Blocked web request for 30+ seconds
        * NEW: Returns immediately with job ID
        */
       @POST
       @Path("/generate")
       @Consumes(MediaType.APPLICATION_JSON)
       @Produces(MediaType.APPLICATION_JSON)
       public Response generateReport(ReportRequest request) {
           // Validate request
           validateReportRequest(request);

           // Generate job ID
           String jobId = UUID.randomUUID().toString();
           request.setReportId(jobId);
           request.setUserId(UserContext.get().getUserId());
           request.setRequestedAt(System.currentTimeMillis());

           // Create initial job record
           createJobRecord(jobId, "QUEUED");

           // Publish to queue (returns immediately)
           messagePublisher.publish("reports", request);

           // Return job ID for tracking
           return Response.accepted()
               .entity(new JobResponse(jobId, "Report generation queued"))
               .header("Location", "/api/reports/" + jobId)
               .build();
       }

       /**
        * Check report generation status
        */
       @GET
       @Path("/{reportId}")
       @Produces(MediaType.APPLICATION_JSON)
       public Response getReportStatus(@PathParam("reportId") String reportId) {
           ReportStatus status = reportStatusService.getStatus(reportId);

           if (status.isComplete()) {
               return Response.ok()
                   .entity(new ReportResponse(reportId, status.getReportUrl()))
                   .build();
           } else if (status.isFailed()) {
               return Response.status(500)
                   .entity(new ErrorResponse("Report generation failed"))
                   .build();
           } else {
               return Response.status(202)
                   .entity(new JobResponse(reportId, "Report generation in progress"))
                   .build();
           }
       }

       /**
        * Download generated report
        */
       @GET
       @Path("/{reportId}/download")
       @Produces("application/pdf")
       public Response downloadReport(@PathParam("reportId") String reportId) {
           ReportStatus status = reportStatusService.getStatus(reportId);

           if (!status.isComplete()) {
               return Response.status(404)
                   .entity(new ErrorResponse("Report not ready"))
                   .build();
           }

           // Get presigned URL from storage service
           String downloadUrl = storageService.getPresignedUrl(status.getReportUrl());

           // Redirect to presigned URL
           return Response.seeOther(URI.create(downloadUrl)).build();
       }
   }
   ```

3. **Job Status Tracking Service** (Agent: Backend)
   ```java
   // orienteer-core/.../jobs/JobStatusService.java
   public class JobStatusService {
       private final RedisSessionManager redisManager;

       /**
        * Create job record
        */
       public void createJob(String jobId, String type, String status) {
           JobStatus job = new JobStatus();
           job.setJobId(jobId);
           job.setType(type);
           job.setStatus(status);
           job.setCreatedAt(System.currentTimeMillis());

           // Store in Redis with TTL (7 days)
           redisManager.saveWithTTL("job:" + jobId, job, 7 * 24 * 3600);
       }

       /**
        * Update job status
        */
       public void updateJobStatus(String jobId, String status) {
           JobStatus job = getStatus(jobId);
           job.setStatus(status);
           job.setUpdatedAt(System.currentTimeMillis());

           redisManager.save("job:" + jobId, job);
       }

       /**
        * Mark job complete
        */
       public void completeJob(String jobId, String resultUrl) {
           JobStatus job = getStatus(jobId);
           job.setStatus("COMPLETED");
           job.setResultUrl(resultUrl);
           job.setCompletedAt(System.currentTimeMillis());

           redisManager.save("job:" + jobId, job);
       }

       /**
        * Mark job failed
        */
       public void failJob(String jobId, String error) {
           JobStatus job = getStatus(jobId);
           job.setStatus("FAILED");
           job.setError(error);
           job.setCompletedAt(System.currentTimeMillis());

           redisManager.save("job:" + jobId, job);
       }

       /**
        * Get job status
        */
       public JobStatus getStatus(String jobId) {
           JobStatus job = redisManager.load("job:" + jobId, JobStatus.class);

           if (job == null) {
               throw new NotFoundException("Job not found: " + jobId);
           }

           return job;
       }
   }
   ```

---

### Task 4: Background Job Scheduling
**12-Factor**: VIII (Concurrency)
**Priority**: MEDIUM
**Estimated Effort**: 5-7 days
**Agent Team**: Backend agent

#### Implementation Steps

1. **Scheduled Job Framework** (Agent: Backend)
   ```java
   // orienteer-worker/.../scheduling/ScheduledJobRunner.java
   public class ScheduledJobRunner {
       private final ScheduledExecutorService scheduler;
       private final MessagePublisher messagePublisher;
       private final List<ScheduledJob> jobs;

       public void start() {
           log.info("Starting scheduled job runner");

           scheduler = Executors.newScheduledThreadPool(5);

           // Register scheduled jobs
           registerJobs();

           log.info("Scheduled {} jobs", jobs.size());
       }

       private void registerJobs() {
           jobs = Arrays.asList(
               new DatabaseCleanupJob(),
               new ReportAggregationJob(),
               new SessionCleanupJob(),
               new DataBackupJob()
           );

           for (ScheduledJob job : jobs) {
               scheduleJob(job);
           }
       }

       private void scheduleJob(ScheduledJob job) {
           // Parse cron expression or use interval
           long initialDelay = job.getInitialDelaySeconds();
           long period = job.getPeriodSeconds();

           scheduler.scheduleAtFixedRate(
               () -> executeJob(job),
               initialDelay,
               period,
               TimeUnit.SECONDS
           );

           log.info("Scheduled job: {} (every {} seconds)",
               job.getName(), period);
       }

       private void executeJob(ScheduledJob job) {
           try {
               log.info("Executing scheduled job: {}", job.getName());

               // Publish job to queue for processing
               JobMessage message = job.createMessage();
               messagePublisher.publish(job.getQueueName(), message);

               log.info("Scheduled job queued: {}", job.getName());

           } catch (Exception e) {
               log.error("Failed to execute scheduled job: " + job.getName(), e);
           }
       }
   }

   // Scheduled job interface
   public interface ScheduledJob {
       String getName();
       String getQueueName();
       long getInitialDelaySeconds();
       long getPeriodSeconds();
       JobMessage createMessage();
   }
   ```

2. **Database Cleanup Job Example** (Agent: Backend)
   ```java
   // orienteer-worker/.../scheduling/DatabaseCleanupJob.java
   public class DatabaseCleanupJob implements ScheduledJob {
       @Override
       public String getName() {
           return "database-cleanup";
       }

       @Override
       public String getQueueName() {
           return "data-processing";
       }

       @Override
       public long getInitialDelaySeconds() {
           return 3600;  // 1 hour
       }

       @Override
       public long getPeriodSeconds() {
           return 86400;  // Daily
       }

       @Override
       public JobMessage createMessage() {
           CleanupJobMessage message = new CleanupJobMessage();
           message.setJobType("database-cleanup");
           message.setOlderThanDays(30);
           return message;
       }
   }
   ```

---

### Task 5: Process-Specific Deployment
**12-Factor**: VIII (Concurrency)
**Priority**: HIGH
**Estimated Effort**: 5-7 days
**Agent Team**: DevOps agent

#### Implementation Steps

1. **Web Process Deployment** (Agent: DevOps)
   ```yaml
   # k8s/base/web-deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: orienteer-web
     labels:
       app: orienteer
       process-type: web
   spec:
     replicas: 4
     selector:
       matchLabels:
         app: orienteer
         process-type: web
     template:
       metadata:
         labels:
           app: orienteer
           process-type: web
       spec:
         containers:
         - name: orienteer
           image: orienteer:${IMAGE_TAG}
           command: ["java", "-jar", "/app/orienteer-web.jar"]
           ports:
           - containerPort: 8080
             name: http
           env:
           - name: PROCESS_TYPE
             value: "web"
           - name: JAVA_OPTS
             value: "-Xmx512m -Xms256m"
           envFrom:
           - configMapRef:
               name: orienteer-config
           - secretRef:
               name: orienteer-secrets
           resources:
             requests:
               memory: "512Mi"
               cpu: "250m"
             limits:
               memory: "1Gi"
               cpu: "500m"
           livenessProbe:
             httpGet:
               path: /health/live
               port: 8080
             initialDelaySeconds: 60
             periodSeconds: 10
           readinessProbe:
             httpGet:
               path: /health/ready
               port: 8080
             initialDelaySeconds: 30
             periodSeconds: 5
   ```

2. **Worker Process Deployment** (Agent: DevOps)
   ```yaml
   # k8s/base/worker-deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: orienteer-worker
     labels:
       app: orienteer
       process-type: worker
   spec:
     replicas: 2
     selector:
       matchLabels:
         app: orienteer
         process-type: worker
     template:
       metadata:
         labels:
           app: orienteer
           process-type: worker
       spec:
         containers:
         - name: orienteer
           image: orienteer:${IMAGE_TAG}
           command: ["java", "-jar", "/app/orienteer-worker.jar"]
           env:
           - name: PROCESS_TYPE
             value: "worker"
           - name: WORKER_THREADS
             value: "10"
           - name: JAVA_OPTS
             value: "-Xmx1024m -Xms512m"
           envFrom:
           - configMapRef:
               name: orienteer-config
           - secretRef:
               name: orienteer-secrets
           resources:
             requests:
               memory: "1Gi"
               cpu: "500m"
             limits:
               memory: "2Gi"
               cpu: "1000m"
           livenessProbe:
             exec:
               command:
               - /bin/sh
               - -c
               - pgrep -f orienteer-worker
             initialDelaySeconds: 60
             periodSeconds: 10
   ```

3. **Horizontal Pod Autoscaler** (Agent: DevOps)
   ```yaml
   # k8s/base/web-hpa.yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: orienteer-web
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: orienteer-web
     minReplicas: 2
     maxReplicas: 20
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
     - type: Resource
       resource:
         name: memory
         target:
           type: Utilization
           averageUtilization: 80
     behavior:
       scaleUp:
         stabilizationWindowSeconds: 60
         policies:
         - type: Percent
           value: 50
           periodSeconds: 60
       scaleDown:
         stabilizationWindowSeconds: 300
         policies:
         - type: Percent
           value: 10
           periodSeconds: 60
   ---
   # k8s/base/worker-hpa.yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: orienteer-worker
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: orienteer-worker
     minReplicas: 2
     maxReplicas: 10
     metrics:
     - type: External
       external:
         metric:
           name: rabbitmq_queue_depth
           selector:
             matchLabels:
               queue: emails
         target:
           type: AverageValue
           averageValue: "10"  # Scale when >10 messages per worker
   ```

---

## Testing Requirements

### Unit Tests (Agent: Testing)
```java
// MessagePublisherTest.java
@Test
public void testPublishMessage() {
    EmailMessage message = new EmailMessage();
    message.setTo("test@example.com");

    messagePublisher.publish("emails", message);

    // Verify message published to queue
    verify(channel).basicPublish(eq(""), eq("emails"), any(), any());
}

// EmailMessageHandlerTest.java
@Test
public void testEmailHandling() throws Exception {
    EmailMessage message = new EmailMessage();
    message.setTo("test@example.com");

    emailHandler.handle(message);

    // Verify email sent
    verify(mailService).send(message);
}
```

### Integration Tests (Agent: Testing)
```java
// AsyncEmailTest.java
@Test
public void testAsyncEmailSending() {
    // Submit email via REST API
    Response response = sendEmail(emailRequest);
    assertEquals(202, response.getStatus());

    String jobId = response.readEntity(JobResponse.class).getJobId();

    // Wait for processing
    await().atMost(30, SECONDS).until(() -> {
        JobStatus status = getJobStatus(jobId);
        return status.getStatus().equals("COMPLETED");
    });

    // Verify email was sent
    assertTrue(emailWasSent(emailRequest));
}

// WorkerScalingTest.java
@Test
public void testWorkerScaling() {
    // Queue 100 jobs
    List<String> jobIds = queueJobs(100);

    // Verify initial worker count
    assertEquals(2, getWorkerPodCount());

    // Wait for auto-scaling
    await().atMost(2, MINUTES).until(() -> {
        return getWorkerPodCount() > 2;
    });

    // Verify all jobs processed
    await().atMost(5, MINUTES).until(() -> {
        return allJobsCompleted(jobIds);
    });
}
```

### Performance Tests (Agent: Performance)
```javascript
// k6-async-test.js
export default function() {
    // Submit report generation
    let res = http.post('http://orienteer/api/reports/generate', {
        reportType: 'monthly',
        params: { month: '2025-10' }
    });

    check(res, {
        'status is 202': (r) => r.status === 202,
        'response time < 200ms': (r) => r.timings.duration < 200,
    });

    let jobId = res.json('jobId');

    // Poll for completion
    let completed = false;
    let attempts = 0;

    while (!completed && attempts < 60) {
        sleep(1);

        let statusRes = http.get(`http://orienteer/api/reports/${jobId}`);

        if (statusRes.status === 200) {
            completed = true;
        }

        attempts++;
    }

    check(completed, {
        'report generated within 60s': (c) => c === true,
    });
}
```

---

## Agent Coordination Plan

```javascript
[Single Message - Parallel Execution]:
  Task("Infrastructure Lead", "
    Deploy RabbitMQ cluster.
    Configure queue infrastructure.
  ", "cicd-engineer")

  Task("Backend Developer 1", "
    Implement message queue integration.
    Create MessagePublisher and handlers.
  ", "backend-dev")

  Task("Backend Developer 2", "
    Implement Worker process application.
    Create message handlers for email, reports, data.
  ", "backend-dev")

  Task("Backend Developer 3", "
    Convert web endpoints to async.
    Implement job status tracking.
  ", "backend-dev")

  Task("DevOps Engineer", "
    Create separate deployments for web/worker.
    Configure auto-scaling for both process types.
  ", "cicd-engineer")

  Task("Testing Engineer", "
    Write comprehensive tests.
    Perform load and scaling tests.
  ", "tester")

  TodoWrite { todos: [
    {content: "Deploy RabbitMQ cluster", status: "pending"},
    {content: "Implement QueueConnectionFactory", status: "pending"},
    {content: "Create MessagePublisher", status: "pending"},
    {content: "Implement Worker process", status: "pending"},
    {content: "Create message handlers", status: "pending"},
    {content: "Convert email endpoint to async", status: "pending"},
    {content: "Convert report generation to async", status: "pending"},
    {content: "Implement job status tracking", status: "pending"},
    {content: "Create scheduled job framework", status: "pending"},
    {content: "Create web/worker deployments", status: "pending"},
    {content: "Configure auto-scaling", status: "pending"},
    {content: "Write comprehensive tests", status: "pending"}
  ]}
```

---

## Deliverables Checklist

- [ ] RabbitMQ cluster deployed and configured
- [ ] Queue connection manager implemented
- [ ] Message publisher implemented
- [ ] Worker process application created
- [ ] Email message handler
- [ ] Report generation handler
- [ ] Data processing handler
- [ ] Workflow execution handler
- [ ] Async email endpoint
- [ ] Async report generation endpoint
- [ ] Job status tracking service
- [ ] Scheduled job framework
- [ ] Separate web/worker deployments
- [ ] Horizontal pod autoscalers configured
- [ ] Queue depth monitoring
- [ ] Unit tests: 85%+ coverage
- [ ] Integration tests passing
- [ ] Load tests: 1000+ concurrent users
- [ ] Documentation updated

---

## Success Validation

### Manual Testing
```bash
# Test 1: Submit async email
curl -X POST http://localhost:8080/api/emails \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"to":"test@example.com","subject":"Test","body":"Test"}'
# Should return: 202 Accepted with jobId

# Test 2: Check job status
curl http://localhost:8080/api/emails/$JOB_ID/status
# Should return: job status (QUEUED, PROCESSING, COMPLETED)

# Test 3: Verify web request speed
time curl http://localhost:8080/api/emails -X POST ...
# Should complete in < 200ms

# Test 4: Scale workers
kubectl scale deployment orienteer-worker --replicas=10
# All jobs should continue processing

# Test 5: Monitor queue depth
curl http://rabbitmq-management:15672/api/queues
# Should show queue depth and consumer counts
```

---

**Next Phase**: [Phase 4 - Cloud-Native Features](05-PHASE-4-CLOUD-NATIVE-FEATURES.md)

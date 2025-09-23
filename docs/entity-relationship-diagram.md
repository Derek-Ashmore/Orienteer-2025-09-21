# Orienteer Business Domain Entity Relationship Diagram

## Core Entity Relationships

```mermaid
erDiagram
    %% Core Security Entities
    OUser ||--o{ OUserSocialNetwork : "has social accounts"
    OUser }o--|| IOPerspective : "has default perspective"
    OUser ||--o{ ORole : "has roles"
    ORole }o--|| IOPerspective : "has perspective"

    %% User Enhancement
    OrienteerUser ||--|| OUser : "extends"
    OrienteerUser ||--o{ OUserSocialNetwork : "manages"

    %% Social Networks
    OUserSocialNetwork }o--|| OAuth2Provider : "uses provider"
    OAuth2Provider ||--o{ OAuth2Service : "configures"
    OAuth2Service ||--o{ OAuth2ServiceContext : "has context"

    %% Localization System
    IOLocalization {
        string key PK
        string language
        string style
        string variation
        string value
        boolean active
    }

    %% Perspective Management
    IOPerspective ||--o{ IOPerspectiveItem : "contains menu items"
    IOPerspectiveItem ||--o{ IOPerspectiveItem : "has sub-items"

    IOPerspective {
        string alias PK
        map name
        string icon
        string homeUrl
        string footer
        set features
    }

    IOPerspectiveItem {
        string alias PK
        map name
        string icon
        string url
    }

    %% Task Management
    IOTask ||--o{ IOTaskSessionPersisted : "has sessions"
    IOTaskSessionPersisted }o--|| IOTask : "belongs to task"
    IOConsoleTask ||--|| IOTask : "extends"

    IOTask {
        string name
        string description
        boolean autodeleteSessions
    }

    IOTaskSessionPersisted {
        string threadName
        enum status
        datetime startTimestamp
        datetime finishTimestamp
        double currentProgress
        double finalProgress
        boolean stopable
        boolean deleteOnFinish
        string output
        string error
    }

    %% Class Domain Classification
    OClass {
        string name PK
        enum domain
        string nameProperty
        string parentProperty
        string defaultTab
        string sortProperty
        enum sortOrder
    }

    OProperty {
        string name PK
        enum type
        string tab
        string visualization
        boolean displayable
        boolean hidden
        boolean uiReadOnly
    }

    OClass ||--o{ OProperty : "has properties"

    %% Module System
    AbstractOrienteerModule {
        string name PK
        int version
        boolean enabled
    }

    %% Document Wrappers
    IODocumentWrapper {
        string rid
        datetime created
        datetime updated
    }

    %% All business entities extend IODocumentWrapper
    IOLocalization ||--|| IODocumentWrapper : "extends"
    IOPerspective ||--|| IODocumentWrapper : "extends"
    IOPerspectiveItem ||--|| IODocumentWrapper : "extends"
    IOTask ||--|| IODocumentWrapper : "extends"
    IOTaskSessionPersisted ||--|| IODocumentWrapper : "extends"
    OrienteerUser ||--|| IODocumentWrapper : "extends"
    OUserSocialNetwork ||--|| IODocumentWrapper : "extends"
```

## Module Dependencies

```mermaid
graph TB
    %% Core Platform
    orienteer-core["orienteer-core<br/>(Platform Core)"]

    %% Core Modules
    orienteer-core --> localization["Localization Module<br/>(IOLocalization)"]
    orienteer-core --> perspectives["Perspectives Module<br/>(IOPerspective)"]
    orienteer-core --> tasks["Task Manager Module<br/>(IOTask)"]
    orienteer-core --> widgets["Widgets Module<br/>(Dashboard)"]

    %% Extension Modules
    orienteer-users["orienteer-users<br/>(OrienteerUser, OAuth2)"]
    orienteer-mail["orienteer-mail<br/>(Email System)"]
    orienteer-notification["orienteer-notification<br/>(Notifications)"]
    orienteer-graph["orienteer-graph<br/>(Graph Features)"]
    orienteer-pages["orienteer-pages<br/>(Dynamic Pages)"]

    %% Dependencies
    orienteer-core --> orienteer-users
    orienteer-core --> orienteer-mail
    orienteer-core --> orienteer-notification
    orienteer-core --> orienteer-graph
    orienteer-core --> orienteer-pages

    %% Cross-dependencies
    orienteer-users --> localization
    orienteer-users --> perspectives
    orienteer-mail --> tasks
    orienteer-notification --> orienteer-mail
```

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant U as User Interface
    participant C as Controller/Page
    participant DAO as DAO Layer
    participant T as Transponder
    participant H as Hooks
    participant DB as OrientDB

    U->>C: User Action
    C->>DAO: Business Operation
    DAO->>T: Create/Provide Wrapper
    T->>DB: Execute Query
    DB-->>H: Trigger Hook
    H->>H: Validate/Transform
    H-->>DB: Continue/Abort
    DB-->>T: Return Document
    T-->>DAO: Return Wrapper
    DAO-->>C: Return Entity
    C-->>U: Update UI
```

## Key Design Patterns

### 1. Entity Definition Pattern
```java
@EntityType(IOLocalization.CLASS_NAME)
@OrienteerOClass(nameProperty = "key")
public interface IOLocalization extends IODocumentWrapper {
    // Property definitions with annotations
}
```

### 2. Hook-Based Business Logic
```java
public class ValidationHook extends ODocumentHookAbstract {
    @Override
    public void onRecordBeforeCreate(ODocument doc) {
        // Validation logic
    }
}
```

### 3. Method Exposure Pattern
```java
@OMethod(icon = FAIconType.play, bootstrap = BootstrapType.SUCCESS)
public default void startTask(IMethodContext ctx) {
    // Business logic
}
```

## Security Architecture

```mermaid
graph LR
    subgraph "Authentication"
        Login[Login Form]
        OAuth2[OAuth2 Providers]
        Session[User Session]
    end

    subgraph "Authorization"
        Roles[ORole Hierarchy]
        Permissions[Resource Permissions]
        Perspective[User Perspective]
    end

    subgraph "Data Access"
        RBAC[Role-Based Access]
        Hooks[Security Hooks]
        Validation[Business Rules]
    end

    Login --> Session
    OAuth2 --> Session
    Session --> Roles
    Roles --> Permissions
    Roles --> Perspective
    Permissions --> RBAC
    RBAC --> Hooks
    Hooks --> Validation
```

## Business Process Flows

### User Registration & Authentication
1. **Registration**: Create OrienteerUser with email validation
2. **OAuth2 Integration**: Link social network accounts
3. **Role Assignment**: Assign default roles and perspective
4. **Session Management**: Track user activity and preferences

### Content Localization
1. **Key Registration**: Auto-create localization entries
2. **Content Translation**: Manage multi-language content
3. **Cache Management**: Invalidate cache on content changes
4. **Best Match Selection**: Score-based algorithm for content selection

### Task Execution
1. **Task Definition**: Create IOTask with parameters
2. **Session Creation**: Start IOTaskSessionPersisted
3. **Progress Tracking**: Update progress and output
4. **Completion Handling**: Cleanup and notifications

This entity relationship model demonstrates Orienteer's comprehensive approach to business application development, with strong emphasis on:
- **Modularity**: Clean separation of concerns
- **Extensibility**: Plugin-based architecture
- **Security**: Role-based access control
- **Internationalization**: Built-in localization support
- **User Experience**: Customizable perspectives and workflows
```mermaid
erDiagram
    USER {
        int id PK
        string username
        string password
        string name
        string role
    }
    
    MEMBER {
        int id PK
        string ho_ten
        string so_dien_thoai
        string email
        boolean is_active
    }
    
    CARD {
        int id PK
        string licensePlate
        string vehicleType
        string ownerName
        string ownerPhone
        string ownerAddress
        datetime issueDate
        datetime validFrom
        datetime validTo
        string status
        string notes
        string color
        int so_lan_gui
        boolean isActive
        int id_thanh_vien FK
    }
    
    PARKING_LOT {
        string licensePlate PK
        datetime entryTime
        string imageBase64
        boolean isMember
        string vehicleType
        string status
        string ownerName
    }
    
    PARKING_HISTORY {
        int id PK
        int card_id FK
        string licensePlate
        string vehicleType
        string ownerName
        datetime timeIn
        datetime timeOut
        string status
        string imageIn
        string imageOut
        string notes
        int memberId FK
        string memberName
        float parkingDuration
        float fee
    }
    
    USER ||--o{ CARD : "manages"
    MEMBER ||--o{ CARD : "has"
    CARD ||--o{ PARKING_HISTORY : "generates"
    PARKING_LOT ||--o{ PARKING_HISTORY : "records"
} 
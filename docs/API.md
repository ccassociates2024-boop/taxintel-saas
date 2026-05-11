# API Documentation

Base URL:

```txt
http://localhost:8000
```

## Auth

```txt
POST /api/v1/auth/register
POST /api/v1/auth/login
```

Both return:

```json
{
  "access_token": "jwt",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "demo@taxintel.ai",
    "full_name": "Demo CA Firm",
    "role": "CA"
  }
}
```

Use:

```txt
Authorization: Bearer <token>
```

## Clients

```txt
GET  /api/v1/clients
POST /api/v1/clients
GET  /api/v1/clients/{client_id}
```

## Uploads

```txt
POST /api/v1/uploads/ais
POST /api/v1/uploads/26as
```

Multipart fields:

```txt
client_id
assessment_year
file
```

## Tax

```txt
POST /api/v1/tax/{client_id}/compute
```

## Recommendations

```txt
POST /api/v1/recommendations/{client_id}/generate
```

## Dashboard

```txt
GET /api/v1/dashboard
```

## Reports

```txt
GET /api/v1/reports/{client_id}/pdf
GET /api/v1/reports/{client_id}/excel
```

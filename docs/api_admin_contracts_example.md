# API Documentation — GET /api/admin/contracts

**Endpoint:** `GET /api/admin/contracts`
**Access:** Admin only (`require_admin` dependency)
**Purpose:** List all platform contracts with pagination for admin Document Registry.

---

## Request

### Headers

| Header | Value | Required |
|--------|-------|----------|
| `Authorization` | `Bearer <JWT>` | Yes |

### Query Parameters

| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| `limit` | int | 50 | 200 | Number of contracts to return |
| `offset` | int | 0 | — | Number of contracts to skip |
| `status_filter` | string | — | — | Filter by status: `draft`, `pending`, `signed`, `expired`, `cancelled` |

### Example curl

```bash
# List all contracts (default pagination)
curl -X GET 'https://app.rekharbor.ru/api/admin/contracts' \
  -H 'Authorization: Bearer <JWT_TOKEN>'

# With pagination and filter
curl -X GET 'https://app.rekharbor.ru/api/admin/contracts?limit=20&offset=0&status_filter=signed' \
  -H 'Authorization: Bearer <JWT_TOKEN>'
```

---

## Response

### 200 OK — AdminContractListResponse

```json
{
  "items": [
    {
      "id": 42,
      "user_id": 7,
      "contract_type": "advertiser_framework",
      "contract_status": "signed",
      "signed_at": "2026-04-01T12:00:00Z",
      "created_at": "2026-03-28T10:30:00Z",
      "template_version": "1.0"
    },
    {
      "id": 41,
      "user_id": 3,
      "contract_type": "owner_service",
      "contract_status": "pending",
      "signed_at": null,
      "created_at": "2026-03-27T15:45:00Z",
      "template_version": "1.0"
    }
  ],
  "total": 156,
  "limit": 50,
  "offset": 0
}
```

### 401 Unauthorized

```json
{
  "detail": "Authorization header missing"
}
```

### 403 Forbidden

```json
{
  "detail": "Forbidden — admin access required"
}
```

---

## Response Schema

### AdminContractItem

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Contract ID |
| `user_id` | int | Owner user ID |
| `contract_type` | string | Type: `owner_service`, `advertiser_campaign`, `advertiser_framework`, `platform_rules`, `privacy_policy`, `tax_agreement` |
| `contract_status` | string | Status: `draft`, `pending`, `signed`, `expired`, `cancelled` |
| `signed_at` | datetime \| null | When contract was signed |
| `created_at` | datetime | When contract was created |
| `template_version` | string | Contract template version used |

### AdminContractListResponse

| Field | Type | Description |
|-------|------|-------------|
| `items` | AdminContractItem[] | Array of contract items |
| `total` | int | Total number of matching contracts |
| `limit` | int | Applied limit |
| `offset` | int | Applied offset |

---

## Notes

- Results are sorted by `created_at` DESC (newest first)
- No sensitive fields are returned (no `pdf_file_path`, `kep_requested`, `signature_method`)
- Uses same response pattern as other admin list endpoints: `{items, total, limit, offset}`

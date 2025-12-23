# API Usage Analytics

## Overview

The API Usage Analytics system tracks all API calls to provide insights into:
- Which endpoints are used most frequently
- How many times each endpoint is invoked
- Response times and performance metrics
- Error rates and success rates
- User activity patterns

## How It Works

### Automatic Tracking

All API requests are automatically tracked via middleware (`api/main.py`). The middleware records:
- **Endpoint**: The API path (e.g., `/tailor`, `/ats/compare`)
- **Method**: HTTP method (GET, POST, PUT, DELETE)
- **Status Code**: Response status code
- **Response Time**: Time taken to process the request (in milliseconds)
- **Client IP**: IP address of the requester
- **User Agent**: Browser/client information
- **User ID**: User identifier (if available)
- **Error Message**: Error details (if status >= 400)
- **Request/Response Size**: Size of request/response bodies

### Database Storage

Usage data is stored in PostgreSQL in the `api_usage` table with the following structure:

```sql
CREATE TABLE api_usage (
    id UUID PRIMARY KEY,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    user_id UUID,
    client_ip VARCHAR(45),
    status_code INTEGER NOT NULL,
    response_time_ms INTEGER,
    request_size_bytes INTEGER,
    response_size_bytes INTEGER,
    user_agent VARCHAR(500),
    error_message TEXT,
    created_at TIMESTAMP NOT NULL
);
```

Indexes are created for efficient querying by:
- Endpoint and date
- User and date
- Status code and date
- Date only

## API Endpoints

### 1. Get Usage Analytics

**Endpoint**: `GET /analytics/usage`

Get aggregated usage statistics for all endpoints.

**Query Parameters**:
- `start_date` (optional): Start date in ISO format (e.g., "2024-01-01T00:00:00")
- `end_date` (optional): End date in ISO format (e.g., "2024-01-31T23:59:59")
- `endpoint` (optional): Filter by specific endpoint
- `limit` (optional, default: 50): Maximum number of results

**Example Request**:
```bash
curl "http://localhost:8000/analytics/usage?start_date=2024-01-01T00:00:00&limit=10"
```

**Example Response**:
```json
{
  "period": {
    "start_date": "2024-01-01T00:00:00",
    "end_date": null
  },
  "total_endpoints": 10,
  "endpoints": [
    {
      "endpoint": "/tailor",
      "method": "POST",
      "total_requests": 1250,
      "avg_response_time_ms": 3450.5,
      "min_response_time_ms": 1200,
      "max_response_time_ms": 8900,
      "success_count": 1180,
      "error_count": 70,
      "success_rate": 0.944
    },
    {
      "endpoint": "/ats/compare",
      "method": "POST",
      "total_requests": 890,
      "avg_response_time_ms": 2100.3,
      "min_response_time_ms": 800,
      "max_response_time_ms": 5600,
      "success_count": 850,
      "error_count": 40,
      "success_rate": 0.955
    }
  ]
}
```

### 2. Get Top Endpoints

**Endpoint**: `GET /analytics/usage/top`

Get the top N most used endpoints.

**Query Parameters**:
- `limit` (optional, default: 10): Number of top endpoints to return
- `days` (optional, default: 7): Number of days to look back

**Example Request**:
```bash
curl "http://localhost:8000/analytics/usage/top?limit=5&days=30"
```

**Example Response**:
```json
{
  "period_days": 30,
  "total_endpoints": 5,
  "top_endpoints": [
    {
      "endpoint": "/tailor",
      "method": "POST",
      "total_requests": 5420,
      "avg_response_time_ms": 3200.5,
      "success_rate": 0.95
    }
  ]
}
```

### 3. Get Endpoint Details

**Endpoint**: `GET /analytics/usage/endpoint/{endpoint_path}`

Get detailed usage records for a specific endpoint.

**Path Parameters**:
- `endpoint_path`: The endpoint path (e.g., `/tailor`, `/ats/compare`)

**Query Parameters**:
- `start_date` (optional): Start date in ISO format
- `end_date` (optional): End date in ISO format
- `limit` (optional, default: 100): Maximum number of records

**Example Request**:
```bash
curl "http://localhost:8000/analytics/usage/endpoint/tailor?days=7&limit=50"
```

**Example Response**:
```json
{
  "endpoint": "/tailor",
  "period": {
    "start_date": null,
    "end_date": null
  },
  "total_records": 50,
  "records": [
    {
      "id": "uuid-here",
      "method": "POST",
      "status_code": 200,
      "response_time_ms": 3450,
      "client_ip": "192.168.1.1",
      "created_at": "2024-01-15T10:30:00",
      "error_message": null
    }
  ]
}
```

### 4. Get Usage Summary

**Endpoint**: `GET /analytics/usage/summary`

Get overall usage summary with key metrics.

**Query Parameters**:
- `days` (optional, default: 7): Number of days to look back

**Example Request**:
```bash
curl "http://localhost:8000/analytics/usage/summary?days=30"
```

**Example Response**:
```json
{
  "period_days": 30,
  "summary": {
    "total_requests": 15230,
    "total_success": 14450,
    "total_errors": 780,
    "error_rate": 0.051,
    "success_rate": 0.949,
    "overall_avg_response_time_ms": 2850.5
  },
  "top_endpoints": [
    {
      "endpoint": "/tailor",
      "method": "POST",
      "total_requests": 5420,
      "success_rate": 0.95
    }
  ],
  "total_unique_endpoints": 15
}
```

## Usage Examples

### Find Most Used APIs

```bash
# Get top 10 most used endpoints in last 7 days
curl "http://localhost:8000/analytics/usage/top?limit=10&days=7"
```

### Analyze Specific Endpoint

```bash
# Get detailed stats for /tailor endpoint
curl "http://localhost:8000/analytics/usage/endpoint/tailor?days=30"
```

### Get Overall Statistics

```bash
# Get summary for last 30 days
curl "http://localhost:8000/analytics/usage/summary?days=30"
```

### Filter by Date Range

```bash
# Get usage for specific date range
curl "http://localhost:8000/analytics/usage?start_date=2024-01-01T00:00:00&end_date=2024-01-31T23:59:59"
```

## Database Migration

To create the `api_usage` table, run Alembic migration:

```bash
# Generate migration
alembic revision --autogenerate -m "Add API usage tracking"

# Apply migration
alembic upgrade head
```

Or manually create the table:

```sql
CREATE TABLE api_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    client_ip VARCHAR(45),
    status_code INTEGER NOT NULL,
    response_time_ms INTEGER,
    request_size_bytes INTEGER,
    response_size_bytes INTEGER,
    user_agent VARCHAR(500),
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_usage_endpoint_created ON api_usage(endpoint, created_at);
CREATE INDEX idx_api_usage_user_created ON api_usage(user_id, created_at);
CREATE INDEX idx_api_usage_status_created ON api_usage(status_code, created_at);
CREATE INDEX idx_api_usage_created ON api_usage(created_at);
```

## Performance Considerations

1. **Asynchronous Tracking**: API usage is tracked asynchronously to avoid blocking requests
2. **Indexed Queries**: All common query patterns are indexed for fast retrieval
3. **Automatic Cleanup**: Consider implementing data retention policies for old records
4. **Batch Inserts**: For high-traffic scenarios, consider batching inserts

## Security

- Analytics endpoints should be protected with authentication
- Consider rate limiting analytics endpoints
- Don't expose sensitive user data in analytics responses
- Filter out internal/admin endpoints from public analytics

## Monitoring

Use the analytics data to:
- Identify most popular features
- Monitor API performance
- Detect unusual traffic patterns
- Track error rates
- Plan capacity and scaling

## Future Enhancements

- Real-time analytics dashboard
- Export analytics data to CSV/JSON
- Alerting on high error rates
- User-specific analytics
- Geographic distribution of requests
- API version tracking


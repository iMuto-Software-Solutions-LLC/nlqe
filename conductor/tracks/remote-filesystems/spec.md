# Remote File Systems Support

## Overview
Enable the Natural Language Query Engine (NLQE) to query remote files stored in S3, Azure Blob Storage, Google Cloud Storage, and via HTTP/HTTPS using DuckDB's `httpfs` extension.

This will allow users to query datasets directly from cloud buckets without needing to download them locally first.

## Requirements

### 1. Remote Path Detection
- Update `DataSourceIntrospector` and `DuckDBExecutor` to recognize remote URI patterns (e.g., `s3://`, `https://`, `azure://`, `gs://`).
- Bypass local file existence checks for these URIs.

### 2. DuckDB `httpfs` Integration
- Automatically install and load the `httpfs` extension when a remote path is detected.
- Support basic configuration for credentials (AWS access keys, Azure connection strings) via environment variables.

### 3. Testing Environment
- Add **MinIO** (S3 compatible) to `docker-compose.yml` to facilitate local integration testing.
- Implement tests that upload a sample `.parquet` file to the local MinIO instance and query it via NLQE.

### 4. Documentation
- Update `README.md` and `docs/API.md` with examples of remote file querying.
- Document the required environment variables for cloud provider authentication.

## Out of Scope
- Implementing manual multi-part upload/download logic. We rely on DuckDB's native streaming capabilities.
- Support for complex VPC/Private Link configurations (standard URI access only).

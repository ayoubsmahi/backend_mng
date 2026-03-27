Drone Service Management Backend

Backend API for a Drone Service Management Application that handles missions, file storage, and financial transactions.
The system is designed to help drone operators manage aerial missions, upload and organize collected data, and track service payments.

Overview

This backend provides APIs for managing:

Drone Missions

Uploaded Data Files

Client Transactions

User Management

Mission Status Tracking

It is designed to support a frontend dashboard where operators can monitor drone operations and manage project data.

File storage

By default, uploads are stored on the local filesystem under `uploads/`. On platforms with ephemeral filesystems (deploy/restart/scale), this will cause previously uploaded files to disappear even though their metadata remains in Postgres.

To store files persistently, configure Cloudflare R2 (S3-compatible) by setting these environment variables:

- `R2_BUCKET`
- `R2_ENDPOINT_URL` (example: `https://<accountid>.r2.cloudflarestorage.com`)
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_REGION` (optional, default `auto`)
- `R2_KEY_PREFIX` (optional)

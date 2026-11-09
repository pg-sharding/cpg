# Artifact locations

This Git report/harness branch retains curated documentation, source patches
and replay inputs. Generated observations, runtime/gate receipts and raw chunks
are retained in the complete immutable internal S3 packet:

`s3://pgtrash/pgbugs-artifacts/hash-noop-buffer-combined-20261109-r1/`

Retrieve that complete packet before using its offline restore/audit commands.
The fresh source/build/fixture/SQL commands can run from this Git directory.
The source-only branch remains at commit 909e76d48524f5f2c9bfed09c01f25195fb1798a.
No regression.diffs, regression.out, PGDATA, binaries or runner logs are committed.

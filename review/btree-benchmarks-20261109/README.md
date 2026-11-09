# B-tree matched SQL delivery

RESULTS.md summarizes the two completed B72 campaigns and source branches.
This Git commit contains curated reports, English UNSENT drafts, alternative
patches and build/reproduction scripts. It does not include generated raw
observations, compiled objects, clusters or full runner logs.

Full lossless frozen packets are delivered separately in the authorized
internal object store (Yandex endpoint https://storage.yandexcloud.net):

- s3://pgtrash/pgbugs-artifacts/btree-ios-v14-sql-20261109-r1/
- s3://pgtrash/pgbugs-artifacts/btree-typed-leaf-v7-sql-20261109-r5/

Obtain the complete packet before running its raw restore commands. Source
branches preserve unsuccessful alternatives; these results do not select V14
as a general V13 upgrade or V7 as a general V6 replacement. Neither letter
has been sent. This documentation commit adds only review/ files.

tar cvf postgres14.tar postgres14
zstd postgres14.tar
tar cvf redis.tar redis
zstd redis.tar
restic -r rclone:google:restic backup postgres14.tar.zst redis.tar.zst
rm postgres14.tar.zst redis.tar.zst
rm postgres14.tar redis.tar
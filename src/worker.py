import os

import redis
import rq

listen = ['high', 'default', 'low']
redis_url = os.getenv('REDISTOGO_URL')
conn = redis.from_url(redis_url)

if __name__ == '__main__':
    with rq.Connection(conn):
        worker = rq.Worker(map(rq.Queue, listen))
        worker.work()

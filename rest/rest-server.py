from flask import Flask, request, jsonify, send_file
import redis
import hashlib
import json
from minio import Minio
import io
import os

app = Flask(__name__)

# Connect to Redis (using service name "redis")
redis_host = os.getenv('REDIS_HOST', 'redis')
redis_client = redis.Redis(host=redis_host, port=6379, db=0)

# Connect to MinIO (using full service name)
minio_host = os.getenv('MINIO_HOST', 'myminio-proj.minio-ns.svc.cluster.local:9000')
minio_client = Minio(
    minio_host,
    access_key=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
    secret_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
    secure=False
)

def log_message(msg):
    """Send log to Redis and print"""
    try:
        redis_client.lpush('logging', msg)
        print(msg)
    except:
        print(msg)

@app.route('/apiv1/separate', methods=['POST'])
def separate():
    """Upload MP3 and queue for processing"""
    try:
        # Get file from form
        if 'mp3' not in request.files:
            return jsonify({"error": "No MP3 file"}), 400
        
        file = request.files['mp3']
        if file.filename == '':
            return jsonify({"error": "Empty filename"}), 400
        
        # Read file
        file_content = file.read()
        
        # Generate unique hash (MD5 of file content)
        song_hash = hashlib.md5(file_content).hexdigest()
        
        log_message(f"REST: Received {file.filename}, hash: {song_hash}")
        
        # Upload to MinIO queue bucket
        minio_client.put_object(
            "queue",
            f"{song_hash}.mp3",
            io.BytesIO(file_content),
            length=len(file_content),
            content_type='audio/mpeg'
        )
        
        log_message(f"REST: Uploaded {song_hash}.mp3 to MinIO")
        
        # Queue job to Redis (LPUSH adds to list)
        job = {"hash": song_hash, "filename": file.filename}
        redis_client.lpush('toWorker', json.dumps(job))
        
        log_message(f"REST: Queued job {song_hash}")
        
        # Return hash to client
        return jsonify({"hash": song_hash}), 200
        
    except Exception as e:
        log_message(f"REST ERROR: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/apiv1/track/<song_hash>/<track_name>', methods=['GET'])
def get_track(song_hash, track_name):
    """Download a separated track"""
    try:
        object_name = f"{song_hash}-{track_name}.mp3"
        log_message(f"REST: Request for {object_name}")
        
        # Download from MinIO output bucket
        try:
            response = minio_client.get_object("output", object_name)
            data = response.read()
            response.close()
            response.release_conn()
            
            # Send file to client
            return send_file(
                io.BytesIO(data),
                mimetype='audio/mpeg',
                as_attachment=True,
                download_name=f"{track_name}.mp3"
            )
        except:
            log_message(f"REST: Track not found - {object_name}")
            return jsonify({"error": "Track not found"}), 404
            
    except Exception as e:
        log_message(f"REST ERROR: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/apiv1/queue', methods=['GET'])
def queue_status():
    """Check how many jobs are queued"""
    try:
        queue_length = redis_client.llen('toWorker')
        return jsonify({"queue_length": queue_length}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    log_message("REST: Server starting")
    app.run(host='0.0.0.0', port=5000, debug=False)

import redis
import json
import os
import subprocess
from minio import Minio
from pathlib import Path
import shutil
import time

# Connect to Redis
redis_host = os.getenv('REDIS_HOST', 'redis')
redis_client = redis.Redis(host=redis_host, port=6379, db=0)

# Connect to MinIO
minio_host = os.getenv('MINIO_HOST', 'myminio-proj.minio-ns.svc.cluster.local:9000')
minio_client = Minio(
    minio_host,
    access_key=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
    secret_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
    secure=False
)

def log_message(msg):
    try:
        redis_client.lpush('logging', msg)
        print(msg)
    except:
        print(msg)

def process_song(song_hash, filename):
    """Process one song"""
    try:
        log_message(f"WORKER: Processing {song_hash}")
        
        # Create temp directory
        temp_dir = Path(f"/tmp/{song_hash}")
        temp_dir.mkdir(exist_ok=True, parents=True)
        
        # Download MP3 from MinIO
        input_file = temp_dir / "input.mp3"
        log_message(f"WORKER: Downloading from MinIO")
        
        minio_client.fget_object("queue", f"{song_hash}.mp3", str(input_file))
        
        log_message(f"WORKER: Downloaded, size: {input_file.stat().st_size} bytes")
        
        # Run Demucs (AI separation)
        log_message(f"WORKER: Running Demucs separation")
        output_dir = temp_dir / "separated"
        output_dir.mkdir(exist_ok=True)
        
        cmd = [
            "python3", "-m", "demucs",
            "-n", "htdemucs",  # Model name
            "--out", str(output_dir),
            str(input_file)
        ]
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
        elapsed = time.time() - start_time
        
        log_message(f"WORKER: Demucs completed in {elapsed:.1f} seconds")
        
        if result.returncode != 0:
            log_message(f"WORKER ERROR: Demucs failed")
            return False
        
        # Find separated tracks
        separated_path = output_dir / "htdemucs" / "input"
        
        if not separated_path.exists():
            log_message(f"WORKER ERROR: Output not found")
            return False
        
        log_message(f"WORKER: Found separated tracks")
        
        # Upload each track
        tracks = ['vocals', 'drums', 'bass', 'other']
        uploaded_count = 0
        
        for track in tracks:
            track_file = separated_path / f"{track}.wav"
            
            if track_file.exists():
                output_name = f"{song_hash}-{track}.mp3"
                
                log_message(f"WORKER: Converting {track} to MP3")
                
                # Convert WAV to MP3 using ffmpeg
                mp3_file = temp_dir / f"{track}.mp3"
                convert_cmd = [
                    "ffmpeg", "-i", str(track_file),
                    "-codec:a", "libmp3lame",
                    "-qscale:a", "2",
                    str(mp3_file),
                    "-y"
                ]
                
                convert_result = subprocess.run(convert_cmd, capture_output=True)
                
                if convert_result.returncode == 0 and mp3_file.exists():
                    # Upload to MinIO
                    minio_client.fput_object(
                        "output",
                        output_name,
                        str(mp3_file),
                        content_type='audio/mpeg'
                    )
                    log_message(f"WORKER: Uploaded {output_name}")
                    uploaded_count += 1
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        if uploaded_count > 0:
            log_message(f"WORKER: ✓ Completed {song_hash} - {uploaded_count} tracks")
            return True
        else:
            log_message(f"WORKER ERROR: No tracks uploaded")
            return False
        
    except Exception as e:
        log_message(f"WORKER ERROR: {str(e)}")
        return False

def main():
    """Main loop - wait for jobs"""
    log_message("WORKER: Started and waiting for jobs")
    
    while True:
        try:
            log_message("WORKER: Waiting for job...")
            
            # BRPOP - blocks until job available
            result = redis_client.brpop('toWorker', timeout=0)
            
            if result:
                _, job_data = result
                job = json.loads(job_data)
                
                song_hash = job['hash']
                filename = job.get('filename', 'unknown')
                
                log_message(f"WORKER: Got job {song_hash}")
                
                success = process_song(song_hash, filename)
                
                if success:
                    log_message(f"WORKER: ✓ Success")
                else:
                    log_message(f"WORKER: ✗ Failed")
                    
        except KeyboardInterrupt:
            break
        except Exception as e:
            log_message(f"WORKER ERROR: {str(e)}")
            time.sleep(5)

if __name__ == '__main__':
    main()

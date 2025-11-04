# **Lab 7: Music Separation as a Service (MSaaS) – Solution**

## **Overview**
This lab implements a **distributed Music Source Separation service** using **Kubernetes**, **Google Cloud Platform (GKE)**, and **Facebook’s Demucs AI model**.  
The system separates an uploaded audio file into **vocals, drums, bass, and other components** using a scalable **microservices architecture** with asynchronous processing.

---

## **Architecture Components**

| Component | Description |
|------------|--------------|
| **REST API Service** | Flask-based web service for file uploads and downloads |
| **Worker Service** | Executes Demucs AI model to process audio and generate separated stems |
| **Redis** | Acts as the message queue to manage job processing between API and worker |
| **MinIO** | S3-compatible object storage for input and output audio files |
| **GKE (Kubernetes)** | Orchestrates all microservices (API, Worker, Redis, MinIO) |

---

## **Implementation**

### **1. Environment Setup**
- Cloned the Lab-7 repository:  
  ```bash
  git clone https://github.com/pratik1719/lab7-demucs.git
  cd lab7-demucs
  ```
- Enabled required GCP services:  
  ```bash
  gcloud services enable container.googleapis.com compute.googleapis.com
  ```

---

### **2. Kubernetes Cluster Creation**
Created a 3-node cluster for running distributed services:

```bash
gcloud container clusters create music-separation   --zone us-central1-a   --num-nodes 3   --machine-type n1-standard-4   --disk-size 50
```

---

### **3. Infrastructure Deployment**

#### **Redis Message Queue**
```bash
kubectl apply -f redis/redis-deployment.yaml
kubectl apply -f redis/redis-service.yaml
```

#### **MinIO Object Storage**
```bash
kubectl create namespace minio-ns
kubectl apply -f minio/minio-deployment.yaml
kubectl apply -f minio/minio-external-service.yaml
```

#### **MinIO Console Exposure**
```bash
kubectl apply -f minio-console-service.yaml
kubectl get service -n minio-ns minio-console -w
```
✅ **MinIO Console URL:** [http://34.10.121.234:9001](http://34.10.121.234:9001)

#### **Storage Buckets**
```bash
kubectl apply -f minio/create-buckets.yaml
kubectl wait --for=condition=complete --timeout=60s job/create-buckets
kubectl delete job create-buckets
```

Buckets created:  
- **queue** → input MP3 uploads  
- **output** → Demucs separated results

---

### **4. Application Services**

#### **REST API Service**
```bash
kubectl apply -f api/rest-deployment.yaml
kubectl apply -f api/rest-service.yaml
```

#### **Worker Service**
```bash
kubectl apply -f worker/worker-deployment.yaml
kubectl apply -f worker/worker-service.yaml
```

The worker continuously listens to Redis, downloads input audio from `queue`, runs **Demucs**, and uploads four separated MP3s to the `output` bucket.

---

## **Testing & Usage**

### **1. System Testing**
```bash
EXTERNAL_IP=$(kubectl get service rest -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "REST API endpoint: http://$EXTERNAL_IP:5000"
```

Upload an audio file:
```bash
curl -X POST -F "mp3=@data/short-dreams.mp3" http://$EXTERNAL_IP:5000/apiv1/separate
```

---

### **2. Download Separated Tracks**
Once processing completes, download results:
```bash
curl "http://$EXTERNAL_IP:5000/apiv1/track/$HASH/vocals" -o vocals.mp3
curl "http://$EXTERNAL_IP:5000/apiv1/track/$HASH/drums" -o drums.mp3
curl "http://$EXTERNAL_IP:5000/apiv1/track/$HASH/bass" -o bass.mp3
curl "http://$EXTERNAL_IP:5000/apiv1/track/$HASH/other" -o other.mp3
```

---

## **Performance Metrics**

| Metric | Observation |
|:--|:--|
| **Processing Time** | ~2–3 minutes per song |
| **Output Tracks** | 4 separated components – vocals, drums, bass, other |
| **Storage Efficiency** | MP3 compression reduces size by ~90% compared to WAV |
| **Scalability** | Horizontal scaling enabled through Kubernetes replicas |
| **Load Balancer IP** | `34.10.121.234:9001` (MinIO Console) |

---

## **Results**
✅ Successfully implemented **distributed music separation** system  
✅ Deployed **scalable microservices** architecture on Kubernetes  
✅ Integrated **Demucs AI model** for multi-track separation  
✅ Used **MinIO S3 API** for cloud-based object storage  
✅ Achieved **asynchronous job processing** using Redis Queue  

### Output Verification



**MinIO Console Service**
![MinIO Console](outputs/Image%2011-3-25%20at%209.30%E2%80%AFPM.jpeg)

**Queue Bucket**
![Queue Bucket](outputs/Image%2011-3-25%20at%209.48%E2%80%AFPM.jpeg)

**MinIO Output Bucket**
![Output Bucket](outputs/Image%2011-3-25%20at%209.28%E2%80%AFPM.jpeg)



### Audio Output Files
- [Bass Track](https://github.com/pratik1719/lab7-demucs/blob/0b2188bbceb6883aeb690b2f4246bba0c1dd1c8e/bass.mp3)
- [Drums Track](https://github.com/pratik1719/lab7-demucs/blob/0b2188bbceb6883aeb690b2f4246bba0c1dd1c8e/drums.mp3)
- [Other Track](https://github.com/pratik1719/lab7-demucs/blob/0b2188bbceb6883aeb690b2f4246bba0c1dd1c8e/other.mp3)
- [Vocals Track](https://github.com/pratik1719/lab7-demucs/blob/0b2188bbceb6883aeb690b2f4246bba0c1dd1c8e/vocals.mp3)


All files confirmed under **output/** bucket.

---

## **Conclusion**
This lab demonstrates how to deploy a **cloud-native ML pipeline** on Kubernetes using **Demucs** for AI-based music separation.  
The system showcases integration of **Flask**, **Redis**, **MinIO**, and **Kubernetes** for an end-to-end distributed service with asynchronous task management, scalable processing, and persistent storage.

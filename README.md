# Reflector

This is the code base for the Reflector demo (formerly called agenda-talk-diff) for the leads : Troy Web Consulting panel (A Chat with AWS about AI: Real AI/ML AWS projects and what you should know) on 6/14 at 430PM.

The target deliverable is a local-first live transcription and visualization tool to compare a discussion's target agenda/objectives to the actual discussion live.

To setup, 

1) Check values in config.ini file. Specifically add your OPENAI_APIKEY if you plan to use OpenAI API requests.
2) Run ``` export KMP_DUPLICATE_LIB_OK=True``` in Terminal. [This is taken care of in code, but not reflecting, Will fix this issue later.]
3) Run the script setup_depedencies.sh.

    ``` chmod +x setup_dependencies.sh ```

    ``` sh setup_dependencies.sh  <ENV>```

    
   ENV refers to the intended environment for JAX. JAX is available in several variants, [CPU | GPU | Colab TPU | Google Cloud TPU]
   
   ```ENV``` is :
   
   cpu -> JAX CPU installation

   cuda11 -> JAX CUDA 11.x version

   cuda12 -> JAX CUDA 12.x version (Core Weave has CUDA 12 version, can check with ```nvidia-smi```)

    ```sh setup_dependencies.sh cuda12```

4) ``` pip install -r requirements.txt```


5) Run the Whisper-JAX pipeline. Currently, the repo can take a Youtube video and transcribes/summarizes it.

``` python3 whisjax.py "https://www.youtube.com/watch?v=ihf0S97oxuQ" --transcript transcript.txt summary.txt ```

You can even run it on local file or a file in your configured S3 bucket.

``` python3 whisjax.py "startup.mp4" --transcript transcript.txt summary.txt ```

The script will take care of a few cases like youtube file, local file, video file, audio-only file, 
file in S3, etc. If local file is not present, it can automatically take the file from S3.


**S3 bucket:**
Everything you need for S3 is already configured in config.ini. Only edit it if you need to change it deliberately.

S3 bucket name is mentioned in config.ini. All transfers will happen between this bucket and the local computer where the
script is run.  You need AWS_ACCESS_KEY / AWS_SECRET_KEY to authenticate your calls to S3 (done in config.ini).

For AWS S3 Web UI,
1) Login to AWS management console.
2) Search for S3 in the search bar at the top.
3) Navigate to list the buckets under the current account, if needed and choose your bucket [```reflector-bucket```]
4) You should be able to see items in the bucket. You can upload/download files here directly.


For CLI, 
Refer to the FILE UTIL section below.


**FILE UTIL MDOULE:**

A file_util module has been created to upload/download files with AWS S3 bucket pre-configured using config.ini. 
Though not needed for the workflow, if you need to upload / download file, separately on your own, apart from the pipeline workflow in the script, you can do so by :

Upload:

``` python3 file_util.py upload <object_name_in_S3_bucket>```

Download:

``` python3 file_util.py download <object_name_in_S3_bucket>```


**WORKFLOW:**

1) Specify the input source file from a local, youtube link or upload to S3 if needed and pass it as input to the script.
2) Keep the agenda header topics in a local file named "agenda-headers.txt". This needs to be present where the script is run.
3) Run the script. The script automatically transcribes, summarizes and creates a scatter plot of words & topics in the form of an interactive
HTML file, a sample word cloud and uploads them to the S3 bucket
4) Additional artefacts pushed to S3:
   1) HTML visualiztion file
   2) pandas df in pickle format for others to collaborate and make their own visualizations
   3) Summary, transcript and transcript with timestamps file in text format.

    The script also creates 2 types of mappings.
   1) Timestamp -> The top 2 matched agenda topic
   2) Topic -> All matched timestamps in the transcription

Other visualizations can be planned based on available artefacts or new ones can be created.


NEXT STEPS:

1) Run this demo on a local Mac M1 to test flow and observe the performance
2) Create a pipeline using a microphone to listen to audio chunks to perform transcription realtime (and also efficiently
 summarize it as well) -> *done as part of whisjax_realtime_trial.py*
3) Create a RunPod setup for this feature (mentioned in 1 & 2) and test it end-to-end
4) Perform Speaker Diarization using Whisper-JAX
5) Based on the feasibility of the above points, explore suitable visualizations for transcription & summarization.

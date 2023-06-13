# Reflector

This is the code base for the Reflector demo (formerly called agenda-talk-diff) for the leads : Troy Web Consulting panel (A Chat with AWS about AI: Real AI/ML AWS projects and what you should know) on 6/14 at 430PM.

The target deliverable is a local-first live transcription and visualization tool to compare a discussion's target agenda/objectives to the actual discussion live.

To setup, 

1) Check values in config.ini file. Specifically add your OPENAI_APIKEY.
2) Run ``` export KMP_DUPLICATE_LIB_OK=True``` in Terminal. [This is taken care of in code, but not reflecting, Will fix this issue later.]
3) Run the script setup_depedencies.sh.

    ``` chmod +x setup_dependencies.sh ```

    ``` sh setup_dependencies.sh  <ENV>```

    
   ENV refers to the intended environment for JAX. JAX is available in several variants, [CPU | GPU | Colab TPU | Google Cloud TPU]
   
   ```ENV``` is :
   
   cpu -> JAX CPU installation

   cuda11 -> JAX CUDA 11.x version

   cuda12 -> JAX CUDA 12.x version (Core Weave has CUDA 12 version, can check with ```nvidia-smi```)

    sh setup_dependencies.sh cuda12

4) Run the Whisper-JAX pipeline. Currently, the repo takes a Youtube video and transcribes/summarizes it.

``` python3 whisjax.py "https://www.youtube.com/watch?v=ihf0S97oxuQ" --transcript transcript.txt summary.txt ```

5) ``` pip install -r requirements.txt```



NEXT STEPS:

1) Run this demo on a local Mac M1 to test flow and observe the performance
2) Create a pipeline using microphone to listen to audio chunks to perform transcription realtime (and also efficiently
 summarize it as well) -> *done as part of whisjax_realtime_trial.py*
3) Create a RunPod setup for this feature (mentioned in 1 & 2) and test it end-to-end
4) Perform Speaker Diarization using Whisper-JAX
5) Based on feasibility of above points, explore suitable visualizations for transcription & summarization.

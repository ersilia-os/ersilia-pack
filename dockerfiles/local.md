# Build a model image using Ersilia-Pack locally

1. Make sure your model repository is available within the build context (ie in the directory where this Dockerfile is)
2. You can have Ersilia-pack available within the build context or install it using pip

Build using
```
 docker build -t ersilia-pack/<model-id> .
```

Run using
```
docker run -p 5000:5000 -d ersilia-pack/eos80ch:latest
```
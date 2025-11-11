# Troubleshooting: RAM++ Model Loading

## Issue

RAM++ model (`xinyu1205/recognize-anything-plus-model`) may fail to load with:
```
Unrecognized model in xinyu1205/recognize-anything-plus-model. 
Should have a `model_type` key in its config.json
```

## Why This Happens

RAM++ is a custom model architecture not natively supported by the transformers `AutoModel` class. It requires special loading procedures.

## Solutions

### Solution 1: Use Pipeline API (Recommended)

The code has been updated to try the pipeline API first:

```python
# This is now automatic in the code
pipeline = transformers.pipeline(
    "image-to-text",
    model="xinyu1205/recognize-anything-plus-model",
    device=0,
    model_kwargs={"trust_remote_code": True}
)
```

### Solution 2: Alternative Models

If RAM++ continues to fail, switch to well-supported alternative models:

#### Option A: BLIP (Microsoft) - Image Captioning
```python
# config/settings.py
RAM_MODEL_NAME = "Salesforce/blip-image-captioning-large"
```

**Pros**: Well-supported, generates descriptive captions
**Cons**: Returns captions, not direct object tags

#### Option B: CLIP Zero-Shot Classification
Use OpenCLIP (already in the system) for zero-shot object classification:

```python
# You can query specific objects directly
candidate_labels = ["iPhone", "pizza", "laptop", "person", "food"]
# Use CLIP to classify
```

**Pros**: Already loaded, very fast
**Cons**: Need to predefine candidate labels

#### Option C: OWL-ViT (Google) - Open-Vocabulary Object Detection
```python
# config/settings.py
RAM_MODEL_NAME = "google/owlvit-base-patch32"
```

**Pros**: Text-conditioned object detection, well-supported
**Cons**: Requires text prompts for objects

### Solution 3: Use Official RAM Repository

Clone and use the official RAM repository:

```bash
git clone https://github.com/xinyu1205/recognize-anything.git
cd recognize-anything

# Follow their installation instructions
pip install -r requirements.txt
```

Then modify `workers/ai_models.py` to use their custom loading code.

## Current Implementation

The code now:
1. **Tries** pipeline API first
2. **Falls back** to AutoModel with trust_remote_code=True
3. **Logs** detailed errors to help debugging
4. **Suggests** alternatives if both fail

## Recommendation for Prototype

**For immediate testing**, if RAM++ continues to fail:

1. Switch to BLIP for now:
   ```bash
   # Edit .env or config/settings.py
   RAM_MODEL_NAME=Salesforce/blip-image-captioning-large
   ```

2. Use OpenCLIP for object detection (it's already working!)
   - Can do zero-shot classification
   - Already generates embeddings for search

3. Continue with the prototype and validate the workflow

4. Come back to RAM++ optimization later

## Check if RAM++ Loaded Successfully

```bash
# Run validation
python scripts/validate_system.py

# Check logs
# Should see: "✓ RAM++ model loaded via pipeline" or "via AutoModel"
```

If you see errors, check the Celery worker logs when it starts to see which method worked.

## Alternative: Lightweight Object Detection

For production, consider:
- **YOLO-World**: Open-vocabulary object detection
- **GroundingDINO**: Zero-shot object detection
- **OWL-ViT**: Google's open-vocabulary detector

All of these are better supported than RAM++ in the transformers library.


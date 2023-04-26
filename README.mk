gcloud functions deploy pose_detection \
  --entry-point pose_detection \
  --runtime python39 \
  --trigger-event "providers/cloud.firestore/eventTypes/document.create" \
  --trigger-resource "projects/athlete-crowd-dev/databases/(default)/documents/user/{userId}/pre_motion_record/{preMotionRecordId}"
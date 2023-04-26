gcloud functions deploy test \
--gen2 \
--region=asia-northeast1 \
--runtime=python39 \
--entry-point=test \
--trigger-event-filters="type=google.cloud.firestore.document.v1.created" \
--trigger-event-filters="database=(default)" \
--trigger-event-filters-path-pattern="document=user/{userId}/pre_motion_record/{preMotionRecordId}"

gcloud functions deploy pose_detection \
  --entry-point pose_detection \
  --runtime python39 \
  --trigger-event "providers/cloud.firestore/eventTypes/document.create" \
  --trigger-resource "projects/athlete-crowd-dev/databases/(default)/documents/user/{userId}/pre_motion_record/{preMotionRecordId}"

  https://firebasestorage.googleapis.com/v0/b/athlete-crowd-dev.appspot.com/o/uploaded%2Fvideo%2FpBsYRtAP2VTfOL035Hek5zyIqeT2%2Ftest-trim.mp4?alt=media&token=2470acde-ceb2-4fe8-9200-9b4893a0621a
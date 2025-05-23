import cv2
import numpy as np
from typing import List, Dict
import json
from pathlib import Path

IMAGE_PATH = 'tests/test.jpg'
OUTPUT_PATH = 'tests/result.jpg'

sample_response = {
  "user_id": "guest_aa41a295-8271-4eb5-ba31-084ff89f88ed",
  "timestamp": "2025-05-23T21:09:13.331456",
  "detection_id": "db37dc4c-8aa3-48e5-a670-8d39dcd7ba66",
  "detection_results": {
    "faces": [
      {
        "box": [
          3128,
          1194,
          491,
          508
        ],
        "emotions": [
          {
            "emotion": "happy",
            "score": 0.9609110951423645,
            "percentage": 96.09110951423645
          },
          {
            "emotion": "surprise",
            "score": 0.020338669419288635,
            "percentage": 2.0338669419288635
          },
          {
            "emotion": "neutral",
            "score": 0.006129550747573376,
            "percentage": 0.6129550747573376
          },
          {
            "emotion": "disgust",
            "score": 0.004305678885430098,
            "percentage": 0.43056788854300976
          },
          {
            "emotion": "fear",
            "score": 0.0038388066459447145,
            "percentage": 0.38388066459447145
          },
          {
            "emotion": "angry",
            "score": 0.002314232522621751,
            "percentage": 0.23142325226217508
          },
          {
            "emotion": "sad",
            "score": 0.002161917043849826,
            "percentage": 0.21619170438498259
          }
        ]
      },
      {
        "box": [
          2052,
          1053,
          538,
          557
        ],
        "emotions": [
          {
            "emotion": "happy",
            "score": 0.9810478091239929,
            "percentage": 98.10478091239929
          },
          {
            "emotion": "neutral",
            "score": 0.006955406628549099,
            "percentage": 0.6955406628549099
          },
          {
            "emotion": "surprise",
            "score": 0.004240297246724367,
            "percentage": 0.4240297246724367
          },
          {
            "emotion": "fear",
            "score": 0.00219760206528008,
            "percentage": 0.21976020652800798
          },
          {
            "emotion": "sad",
            "score": 0.002158690942451358,
            "percentage": 0.21586909424513578
          },
          {
            "emotion": "disgust",
            "score": 0.0021015950478613377,
            "percentage": 0.21015950478613377
          },
          {
            "emotion": "angry",
            "score": 0.001298612100072205,
            "percentage": 0.1298612100072205
          }
        ]
      },
      {
        "box": [
          3735,
          785,
          608,
          629
        ],
        "emotions": [
          {
            "emotion": "surprise",
            "score": 0.41834738850593567,
            "percentage": 41.83473885059357
          },
          {
            "emotion": "neutral",
            "score": 0.18468479812145233,
            "percentage": 18.468479812145233
          },
          {
            "emotion": "happy",
            "score": 0.1280815303325653,
            "percentage": 12.80815303325653
          },
          {
            "emotion": "fear",
            "score": 0.10819413512945175,
            "percentage": 10.819413512945175
          },
          {
            "emotion": "angry",
            "score": 0.0902055948972702,
            "percentage": 9.02055948972702
          },
          {
            "emotion": "disgust",
            "score": 0.042834579944610596,
            "percentage": 4.28345799446106
          },
          {
            "emotion": "sad",
            "score": 0.027652014046907425,
            "percentage": 2.7652014046907425
          }
        ]
      },
      {
        "box": [
          42,
          725,
          595,
          615
        ],
        "emotions": [
          {
            "emotion": "happy",
            "score": 0.9712433218955994,
            "percentage": 97.12433218955994
          },
          {
            "emotion": "neutral",
            "score": 0.009193025529384613,
            "percentage": 0.9193025529384613
          },
          {
            "emotion": "surprise",
            "score": 0.008883370086550713,
            "percentage": 0.8883370086550713
          },
          {
            "emotion": "disgust",
            "score": 0.003255644114688039,
            "percentage": 0.3255644114688039
          },
          {
            "emotion": "fear",
            "score": 0.002735875081270933,
            "percentage": 0.2735875081270933
          },
          {
            "emotion": "sad",
            "score": 0.0023897401988506317,
            "percentage": 0.23897401988506317
          },
          {
            "emotion": "angry",
            "score": 0.002299041021615267,
            "percentage": 0.22990410216152668
          }
        ]
      },
      {
        "box": [
          4791,
          598,
          597,
          618
        ],
        "emotions": [
          {
            "emotion": "happy",
            "score": 0.9727300405502319,
            "percentage": 97.2730040550232
          },
          {
            "emotion": "surprise",
            "score": 0.011306507512927055,
            "percentage": 1.1306507512927055
          },
          {
            "emotion": "angry",
            "score": 0.003758927108719945,
            "percentage": 0.3758927108719945
          },
          {
            "emotion": "neutral",
            "score": 0.0037041776813566685,
            "percentage": 0.37041776813566685
          },
          {
            "emotion": "disgust",
            "score": 0.0031479038298130035,
            "percentage": 0.31479038298130035
          },
          {
            "emotion": "fear",
            "score": 0.002838573884218931,
            "percentage": 0.2838573884218931
          },
          {
            "emotion": "sad",
            "score": 0.0025138130877166986,
            "percentage": 0.25138130877166986
          }
        ]
      },
      {
        "box": [
          1169,
          376,
          521,
          539
        ],
        "emotions": [
          {
            "emotion": "happy",
            "score": 0.9128754734992981,
            "percentage": 91.28754734992981
          },
          {
            "emotion": "neutral",
            "score": 0.027073495090007782,
            "percentage": 2.707349509000778
          },
          {
            "emotion": "surprise",
            "score": 0.026332294568419456,
            "percentage": 2.6332294568419456
          },
          {
            "emotion": "angry",
            "score": 0.011676277965307236,
            "percentage": 1.1676277965307236
          },
          {
            "emotion": "fear",
            "score": 0.00973626971244812,
            "percentage": 0.973626971244812
          },
          {
            "emotion": "disgust",
            "score": 0.00698047736659646,
            "percentage": 0.698047736659646
          },
          {
            "emotion": "sad",
            "score": 0.005325695034116507,
            "percentage": 0.5325695034116507
          }
        ]
      }
    ],
    "processing_time": 22.855907917022705
  }
}

def draw_detection(image_path: str, detection: Dict, output_path: str):
    # Đọc ảnh
    img = cv2.imread(image_path)
    if img is None:
        print(f"Không thể đọc ảnh: {image_path}")
        return
    faces = detection["detection_results"]["faces"]
    for face in faces:
        x, y, w, h = face["box"]
        # Vẽ bounding box
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        # Lấy emotion có percentage cao nhất
        top_emotion = max(face["emotions"], key=lambda e: e["percentage"])
        label = f"{top_emotion['emotion']} ({top_emotion['percentage']:.1f}%)"
        # Vẽ label emotion lên trên box
        cv2.putText(img, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
        # Vẽ tất cả các emotion (dạng bar nhỏ bên cạnh box)
        bar_x = x + w + 10
        bar_y = y
        for emo in face["emotions"]:
            bar_length = int(emo["percentage"] * 2)  # scale cho dễ nhìn
            cv2.rectangle(img, (bar_x, bar_y), (bar_x + bar_length, bar_y + 20), (255, 200, 0), -1)
            cv2.putText(img, f"{emo['emotion']} {emo['percentage']:.1f}%", (bar_x, bar_y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1, cv2.LINE_AA)
            bar_y += 25
    cv2.imwrite(output_path, img)
    print(f"Đã lưu ảnh kết quả: {output_path}")

if __name__ == "__main__":
    draw_detection(IMAGE_PATH, sample_response, OUTPUT_PATH) 
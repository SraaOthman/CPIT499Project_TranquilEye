# train_model.py

import os
import cv2
import numpy as np
import joblib
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.decomposition import PCA
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

dataset_path = r"AnimationStyle-30sec"

def extract_advanced_features(video_path, max_frames=10):
    cap = cv2.VideoCapture(video_path)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, frame_count // max_frames)
    features = []
    prev_gray = None
    i = 0

    while cap.isOpened() and len(features) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        if i % step == 0:
            resized = cv2.resize(frame, (64, 64))
            hist = cv2.calcHist([resized], [0, 1, 2], None, [4, 4, 4], [0, 256]*3).flatten()
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 100, 200)
            edge_density = np.mean(edges)
            brightness = np.mean(gray)
            motion = 0
            if prev_gray is not None:
                diff = cv2.absdiff(prev_gray, gray)
                motion = np.mean(diff)
            prev_gray = gray
            features.append(np.concatenate([hist, [edge_density, brightness, motion]]))
        i += 1
    cap.release()
    return features


if __name__ == "__main__":
    all_data = []
    all_labels = []

    for label_folder in os.listdir(dataset_path):
        folder_path = os.path.join(dataset_path, label_folder)
        if os.path.isdir(folder_path):
            print(f"التصنيف: {label_folder}")
            for filename in os.listdir(folder_path):
                if filename.endswith(".mp4"):
                    path = os.path.join(folder_path, filename)
                    feats = extract_advanced_features(path)
                    for f in feats:
                        all_data.append(f)
                        all_labels.append(label_folder)

    X = np.array(all_data)
    le = LabelEncoder()
    y_encoded = le.fit_transform(all_labels)

    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)
    model = Pipeline([("pca", PCA(n_components=50)), ("clf", RandomForestClassifier(n_estimators=100))])
    model.fit(X_train, y_train)

    print("Accuracy: {:.2f}%".format(accuracy_score(y_test, model.predict(X_test)) * 100))
    print(classification_report(y_test, model.predict(X_test), target_names=le.classes_))

    joblib.dump(model, "style_model.pkl")
    joblib.dump(le, "label_encoder.pkl")


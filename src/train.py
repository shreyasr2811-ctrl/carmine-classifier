"""
!!! SUPERSEDED - DO NOT USE FOR REPORTED RESULTS !!!

This script splits the data at the PATCH level. Because many patches come
from the same patient (same slide, same staining batch, same scanner), the
same patient ends up in BOTH the training and test sets. In the 3,000-image
sample this affected 247 of 274 patients, and it inflated accuracy by about
1.7 percentage points.

Use src/train_grouped.py instead. It splits by patient so no patient appears
on both sides, and it reports cross-validated results.

This file is kept only so the leaky baseline can be reproduced for comparison.
"""

"""
Train a benign/malignant classifier on IDC breast histopathology patches
using handcrafted features + classical ML (Random Forest and XGBoost,
picking whichever performs better on the validation set).

Usage:
    python src/train.py --data_dir data/idc_sample --out_dir models
"""

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from joblib import dump
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support, roc_auc_score,
    confusion_matrix, classification_report,
)
from xgboost import XGBClassifier

sys.path.insert(0, os.path.dirname(__file__))
from features import extract_features_from_path  # noqa: E402


def build_manifest(data_dir):
    rows = []
    for label_str in ("0", "1"):
        cls_dir = os.path.join(data_dir, label_str)
        if not os.path.isdir(cls_dir):
            continue
        for fname in os.listdir(cls_dir):
            if fname.lower().endswith(".png"):
                rows.append({"path": os.path.join(cls_dir, fname), "label": int(label_str)})
    return pd.DataFrame(rows)


def extract_all_features(df, log_every=500):
    feats = []
    t0 = time.time()
    for i, path in enumerate(df["path"].tolist()):
        feats.append(extract_features_from_path(path))
        if (i + 1) % log_every == 0:
            elapsed = time.time() - t0
            print(f"  extracted {i + 1}/{len(df)} ({elapsed:.1f}s elapsed)")
    return np.vstack(feats)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_dir", default="data/idc_sample")
    ap.add_argument("--out_dir", default="models")
    ap.add_argument("--test_size", type=float, default=0.15)
    ap.add_argument("--val_size", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    print("Building manifest...")
    df = build_manifest(args.data_dir)
    print(f"Total images: {len(df)}  (class0={sum(df.label == 0)}, class1={sum(df.label == 1)})")

    train_df, temp_df = train_test_split(
        df, test_size=args.test_size + args.val_size, stratify=df["label"], random_state=args.seed
    )
    rel_test = args.test_size / (args.test_size + args.val_size)
    val_df, test_df = train_test_split(
        temp_df, test_size=rel_test, stratify=temp_df["label"], random_state=args.seed
    )
    print(f"Split -> train={len(train_df)} val={len(val_df)} test={len(test_df)}")

    print("Extracting features (train)...")
    X_train = extract_all_features(train_df)
    print("Extracting features (val)...")
    X_val = extract_all_features(val_df)
    print("Extracting features (test)...")
    X_test = extract_all_features(test_df)

    y_train, y_val, y_test = train_df["label"].values, val_df["label"].values, test_df["label"].values

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)
    X_test_s = scaler.transform(X_test)

    candidates = {
        "random_forest": RandomForestClassifier(
            n_estimators=400, max_depth=None, min_samples_leaf=2,
            n_jobs=-1, random_state=args.seed, class_weight="balanced",
        ),
        "xgboost": XGBClassifier(
            n_estimators=400, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, eval_metric="logloss",
            n_jobs=-1, random_state=args.seed,
        ),
    }

    results = {}
    best_name, best_model, best_auc = None, None, -1
    for name, model in candidates.items():
        print(f"\nTraining {name}...")
        model.fit(X_train_s, y_train)
        val_probs = model.predict_proba(X_val_s)[:, 1]
        val_preds = (val_probs >= 0.5).astype(int)
        auc = roc_auc_score(y_val, val_probs)
        acc = accuracy_score(y_val, val_preds)
        p, r, f1, _ = precision_recall_fscore_support(y_val, val_preds, average="binary")
        print(f"  {name}: val_acc={acc:.4f} val_auc={auc:.4f} val_f1={f1:.4f}")
        results[name] = {"val_acc": acc, "val_auc": auc, "val_precision": p, "val_recall": r, "val_f1": f1}
        if auc > best_auc:
            best_auc, best_name, best_model = auc, name, model

    print(f"\nBest model on validation: {best_name} (AUC={best_auc:.4f})")

    test_probs = best_model.predict_proba(X_test_s)[:, 1]
    test_preds = (test_probs >= 0.5).astype(int)
    test_acc = accuracy_score(y_test, test_preds)
    test_auc = roc_auc_score(y_test, test_probs)
    cm = confusion_matrix(y_test, test_preds)
    report = classification_report(y_test, test_preds, target_names=["benign", "malignant(IDC)"])

    print(f"\nTest accuracy: {test_acc:.4f}  Test AUC: {test_auc:.4f}")
    print("Confusion matrix:\n", cm)
    print(report)

    dump(best_model, os.path.join(args.out_dir, "classifier.joblib"))
    dump(scaler, os.path.join(args.out_dir, "scaler.joblib"))

    metadata = {
        "best_model": best_name,
        "val_results": results,
        "test_accuracy": test_acc,
        "test_auc": test_auc,
        "confusion_matrix": cm.tolist(),
        "n_train": len(train_df),
        "n_val": len(val_df),
        "n_test": len(test_df),
        "feature_dim": int(X_train.shape[1]),
    }
    with open(os.path.join(args.out_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nSaved model, scaler, and metadata to {args.out_dir}/")


if __name__ == "__main__":
    main()

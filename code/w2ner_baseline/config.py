import json
import os


class Config:
    def __init__(self, args):
        with open(args.config, "r", encoding="utf-8") as f:
            config = json.load(f)

        self.__dict__.update(config)
        for k, v in vars(args).items():
            if v is not None:
                self.__dict__[k] = v

        self.output_dir = getattr(self, "output_dir", "./runs/w2ner")
        self.data_dir = getattr(self, "data_dir", "./data/t2know_disjoint")
        self.dataset = getattr(self, "dataset", os.path.basename(self.data_dir.rstrip("/")))
        self.nnw_threshold = getattr(self, "nnw_threshold", 0.5)
        self.thw_threshold = getattr(self, "thw_threshold", 0.5)
        self.num_workers = getattr(self, "num_workers", 4)
        self.max_pos_weight = getattr(self, "max_pos_weight", 50.0)
        self.save_path = os.path.join(self.output_dir, "model.pt")
        self.eval_dir = os.path.join(self.output_dir, "eval_test")
        self.predict_path = os.path.join(self.eval_dir, "pred.jsonl")
        self.gold_path = os.path.join(self.eval_dir, "gold.jsonl")
        self.metrics_csv = os.path.join(self.eval_dir, "per_label_metrics.csv")
        self.global_metrics_path = os.path.join(self.eval_dir, "global_metrics.json")
        self.summary_path = os.path.join(self.eval_dir, "summary.json")

    def __repr__(self):
        return f"{self.__dict__.items()}"

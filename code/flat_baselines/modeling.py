from typing import Optional, Tuple, Union

import torch
from torch.nn import BCEWithLogitsLoss, Dropout, Linear
from transformers import AutoConfig, BertModel, BertPreTrainedModel
from transformers.modeling_outputs import TokenClassifierOutput


class BertForSpanClassification(BertPreTrainedModel):
    config_class = AutoConfig
    base_model_prefix = "bert"

    def __init__(self, config):
        super().__init__(config)
        self.num_labels = config.num_labels
        self.bert = BertModel(config, add_pooling_layer=False)
        dropout_prob = getattr(config, "classifier_dropout", None)
        if dropout_prob is None:
            dropout_prob = getattr(config, "hidden_dropout_prob", 0.1)
        self.dropout = Dropout(dropout_prob)
        self.classifier = Linear(config.hidden_size, config.num_labels)
        self.pos_weight = None
        self.post_init()

    def set_pos_weight(self, pos_weight) -> None:
        self.pos_weight = torch.as_tensor(pos_weight, dtype=torch.float32)

    def forward(
        self,
        input_ids: Optional[torch.Tensor] = None,
        attention_mask: Optional[torch.Tensor] = None,
        token_type_ids: Optional[torch.Tensor] = None,
        position_ids: Optional[torch.Tensor] = None,
        head_mask: Optional[torch.Tensor] = None,
        inputs_embeds: Optional[torch.Tensor] = None,
        labels: Optional[torch.Tensor] = None,
        loss_mask: Optional[torch.Tensor] = None,
        output_attentions: Optional[bool] = None,
        output_hidden_states: Optional[bool] = None,
        return_dict: Optional[bool] = None,
    ) -> Union[Tuple[torch.Tensor], TokenClassifierOutput]:
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            position_ids=position_ids,
            head_mask=head_mask,
            inputs_embeds=inputs_embeds,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )

        sequence_output = outputs[0]
        sequence_output = self.dropout(sequence_output)
        logits = self.classifier(sequence_output)

        loss = None
        if labels is not None:
            pos_weight = None
            if isinstance(self.pos_weight, torch.Tensor):
                pos_weight = self.pos_weight.to(logits.device)
            loss_fct = BCEWithLogitsLoss(reduction="none", pos_weight=pos_weight)
            loss = loss_fct(logits, labels.float())
            if loss_mask is not None:
                mask = loss_mask.float().unsqueeze(-1)
                loss = loss * mask
                denom = mask.sum() * logits.size(-1)
                loss = loss.sum() / denom.clamp_min(1.0)
            else:
                loss = loss.mean()

        if not return_dict:
            output = (logits,) + outputs[2:]
            return ((loss,) + output) if loss is not None else output

        return TokenClassifierOutput(
            loss=loss,
            logits=logits,
            hidden_states=outputs.hidden_states,
            attentions=outputs.attentions,
        )


def build_model(model_name: str, id2label: dict[int, str], label2id: dict[str, int]):
    config = AutoConfig.from_pretrained(model_name, num_labels=len(id2label), id2label=id2label, label2id=label2id)
    if getattr(config, "model_type", None) != "bert":
        raise ValueError(
            f"Unsupported encoder architecture for this runner: {config.model_type}. "
            "code/flat_baselines currently supports BERT-family checkpoints only."
        )
    return BertForSpanClassification.from_pretrained(model_name, config=config)

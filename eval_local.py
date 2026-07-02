"""Evaluate a local HF model (optionally + LoRA adapter) on a NAF-Bench set."""
import argparse, os, json
os.environ.setdefault("HF_HUB_OFFLINE", "1")
import torch
from transformers import AutoConfig, AutoTokenizer, AutoModelForCausalLM
from transformers.models.qwen3 import Qwen3Config
from transformers.models.qwen3.modeling_qwen3 import Qwen3ForCausalLM
from transformers.models.qwen3_moe import Qwen3MoeConfig
from transformers.models.qwen3_moe.modeling_qwen3_moe import Qwen3MoeForCausalLM
from nafbench.answer import parse_answer


class Qwen35Config(Qwen3Config):
    model_type = "qwen3_5"


class Qwen35MoeConfig(Qwen3MoeConfig):
    model_type = "qwen3_5_moe"


class Qwen35ForCausalLM(Qwen3ForCausalLM):
    config_class = Qwen35Config


class Qwen35MoeForCausalLM(Qwen3MoeForCausalLM):
    config_class = Qwen35MoeConfig


class _DictConfig(dict):
    def to_dict(self):
        return dict(self)


from transformers.models.auto.configuration_auto import CONFIG_MAPPING_NAMES
# Newer transformers (>=5.5) ship native Qwen3.5 support; only install the local
# shim when the running transformers doesn't already know the type, otherwise the
# custom config classes shadow the native ones and AutoModel can't map them.
NATIVE_Q35 = "qwen3_5" in CONFIG_MAPPING_NAMES
if not NATIVE_Q35:
    try:
        AutoConfig.register("qwen3_5", Qwen35Config)
        AutoConfig.register("qwen3_5_moe", Qwen35MoeConfig)
        AutoModelForCausalLM.register(Qwen35Config, Qwen35ForCausalLM)
        AutoModelForCausalLM.register(Qwen35MoeConfig, Qwen35MoeForCausalLM)
    except Exception:
        pass

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="google/gemma-3-4b-it")
ap.add_argument("--adapter", default=None)
ap.add_argument("--set", default="data/wfs_big.json")
ap.add_argument("--tag", default="base")
ap.add_argument("--max_new_tokens", type=int, default=600)
args = ap.parse_args()

tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
if args.model.startswith("Qwen/Qwen3.5-") and not NATIVE_Q35:
    cfg_path = tok.init_kwargs.get("name_or_path", args.model)
    if os.path.isdir(cfg_path):
        cfg_file = os.path.join(cfg_path, "config.json")
    else:
        from huggingface_hub import hf_hub_download
        cfg_file = hf_hub_download(args.model, "config.json")
    with open(cfg_file) as fh:
        cfg_json = json.load(fh)
    config = Qwen35Config.from_dict(cfg_json["text_config"])
    config.text_config = config
else:
    config = AutoConfig.from_pretrained(args.model, trust_remote_code=True)
    if isinstance(getattr(config, "text_config", None), dict):
        config.text_config = _DictConfig(config.text_config)
model = AutoModelForCausalLM.from_pretrained(args.model, config=config,
                                             dtype=torch.bfloat16,
                                             device_map="cuda:0",
                                             trust_remote_code=True)
if args.adapter:
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, args.adapter)
model.eval()

items = json.load(open(args.set))
ans = {}
ctokens = {}
for e in items:
    msgs = [{"role": "user", "content": e["prompt"]}]
    enc = tok.apply_chat_template(msgs, add_generation_prompt=True,
                                  return_tensors="pt", return_dict=True)
    enc = {k: v.to(model.device) for k, v in enc.items()}
    plen = enc["input_ids"].shape[1]
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=args.max_new_tokens, do_sample=False,
                             pad_token_id=tok.eos_token_id)
    txt = tok.decode(out[0, plen:], skip_special_tokens=True)
    ans[e["task_id"]] = parse_answer(txt)
    ctokens[e["task_id"]] = int(out.shape[1] - plen)   # generated (completion) tokens

os.makedirs("data/local_answers", exist_ok=True)
json.dump({"model": args.model, "adapter": args.adapter, "tag": args.tag,
           "answers": ans, "completion_tokens": ctokens},
          open(f"data/local_answers/{args.tag}.json", "w"), indent=1)

# score -- only items that HAVE a gold count; gold=None (cond 'none') is
# unscored, so a None==None match must not be rewarded as "correct".
scored = [e for e in items if e.get("gold") is not None]
div = [e for e in scored if e.get("kind") == "divergent"]
ctl = [e for e in scored if e.get("kind") == "control"]
k = sum(ans[e["task_id"]] == e["gold"] for e in scored)
kd = sum(ans[e["task_id"]] == e["gold"] for e in div)
kc = sum(ans[e["task_id"]] == e["gold"] for e in ctl)
n_none = len(items) - len(scored)
print(f"[{args.tag}] overall {k}/{len(scored)}  divergent {kd}/{len(div)}  "
      f"control {kc}/{len(ctl)}  (unscored gold=None: {n_none})")

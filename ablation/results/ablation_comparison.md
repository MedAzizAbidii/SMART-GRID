| label | component | f1 | roc_auc | pr_auc | mcc | delta_f1 | params | latency_ms |
|---|---|---|---|---|---|---|---|---|
| Embedding dim = 128 | Embedding size | 0.5907 | 0.9370 | 0.6960 | 0.6000 | -0.1432 | 291173 | 0.0542 |
| Latent dim = 32 | Latent dim | 0.5373 | 0.9197 | 0.6683 | 0.5481 | -0.0899 | 115189 | 0.033 |
| Attention -> token-wise FFN | Self-attention | 0.5315 | 0.9642 | 0.6555 | 0.5549 | -0.0841 | 46565 | 0.013 |
| Dense encoder (no Transformer) | Transformer encoder | 0.5315 | 0.9642 | 0.6555 | 0.5549 | -0.0841 | 46565 | 0.0102 |
| LR = 0.001 | Learning rate | 0.5141 | 0.9735 | 0.6600 | 0.5534 | -0.0666 | 113125 | 0.0628 |
| Optimizer = sgd | Optimizer | 0.4821 | 0.9381 | 0.3389 | 0.4861 | -0.0346 | 113125 | 0.0447 |
| Threshold = mad | Threshold strategy | 0.4765 | 0.9749 | 0.5253 | 0.5286 | -0.0291 | 113125 | 0.0282 |
| Embedding dim = 32 | Embedding size | 0.4741 | 0.9709 | 0.4640 | 0.5212 | -0.0266 | 48677 | 0.0228 |
| Activation = leaky_relu | Activation | 0.4561 | 0.9754 | 0.5225 | 0.5095 | -0.0087 | 113125 | 0.0327 |
| Activation = relu | Activation | 0.4555 | 0.9755 | 0.5212 | 0.5063 | -0.0081 | 113125 | 0.0568 |
| Loss = MAE | Reconstruction loss | 0.4554 | 0.9592 | 0.4530 | 0.5197 | -0.0080 | 113125 | 0.0439 |
| Latent dim = 8 | Latent dim | 0.4523 | 0.9637 | 0.4997 | 0.5037 | -0.0048 | 112093 | 0.0242 |
| Heads = 2 | Attention heads | 0.4514 | 0.9757 | 0.5275 | 0.5056 | -0.0039 | 113125 | 0.0305 |
| Heads = 1 | Attention heads | 0.4490 | 0.9747 | 0.5180 | 0.5064 | -0.0015 | 113125 | 0.032 |
| Without XAI attribution | XAI (Integrated Gradients) | 0.4475 | 0.9749 | 0.5253 | 0.5052 | 0.0000 | 113125 | 0.0527 |
| Optimizer = adam | Optimizer | 0.4475 | 0.9748 | 0.5246 | 0.5052 | 0.0000 | 113125 | 0.0528 |
| Transformer + Autoencoder (baseline) | Full proposed model | 0.4475 | 0.9749 | 0.5253 | 0.5052 | 0.0000 | 113125 | 0.0527 |
| No positional encoding | Positional encoding | 0.4444 | 0.9706 | 0.5427 | 0.4974 | 0.0030 | 113125 | 0.0293 |
| Heads = 8 | Attention heads | 0.4430 | 0.9763 | 0.5242 | 0.5016 | 0.0045 | 113125 | 0.0374 |
| Dropout = 0.3 | Dropout | 0.4400 | 0.9677 | 0.4731 | 0.4992 | 0.0075 | 113125 | 0.0551 |
| Batch size = 256 | Batch size | 0.4392 | 0.9756 | 0.4772 | 0.4958 | 0.0083 | 113125 | 0.0358 |
| Layers = 4 | Transformer layers | 0.4362 | 0.9724 | 0.5119 | 0.4934 | 0.0112 | 213093 | 0.0767 |
| Optimizer = rmsprop | Optimizer | 0.4324 | 0.9719 | 0.5173 | 0.4877 | 0.0150 | 113125 | 0.0414 |
| Top-40 features (variance) | Feature selection | 0.4311 | 0.8655 | 0.5186 | 0.4225 | 0.0163 | 107320 | 0.0498 |
| LR = 0.0001 | Learning rate | 0.4290 | 0.9729 | 0.4555 | 0.4876 | 0.0184 | 113125 | 0.042 |
| Top-20 features (variance) | Feature selection | 0.4280 | 0.8788 | 0.4158 | 0.4602 | 0.0194 | 104740 | 0.0734 |
| Threshold = p99 | Threshold strategy | 0.4272 | 0.9749 | 0.5253 | 0.4888 | 0.0203 | 113125 | 0.0282 |
| Layers = 1 | Transformer layers | 0.4267 | 0.9710 | 0.5213 | 0.4830 | 0.0208 | 63141 | 0.0301 |
| Activation = elu | Activation | 0.4267 | 0.9705 | 0.5183 | 0.4830 | 0.0208 | 113125 | 0.0376 |
| Batch size = 64 | Batch size | 0.4177 | 0.9765 | 0.6109 | 0.4812 | 0.0297 | 113125 | 0.0873 |
| No latent bottleneck | Autoencoder bottleneck | 0.4151 | 0.9626 | 0.4368 | 0.4791 | 0.0324 | 110997 | 0.0279 |
| Loss = HUBER | Reconstruction loss | 0.4000 | 0.9769 | 0.5013 | 0.4668 | 0.0475 | 113125 | 0.0447 |
| Dropout = 0.0 | Dropout | 0.3976 | 0.9757 | 0.5718 | 0.4648 | 0.0499 | 113125 | 0.053 |
| Sequence length = 16 | Sequence length | 0.3566 | 0.9563 | 0.4575 | 0.4193 | 0.0908 | 113125 | 0.0542 |
| Sequence length = 32 | Sequence length | 0.2692 | 0.9294 | 0.3360 | 0.3043 | 0.1782 | 113125 | 0.1145 |
| No normalization (raw features) | Normalization | 0.2478 | 0.7193 | 0.1822 | 0.2452 | 0.1997 | 113125 | 0.0265 |
| Threshold = p95 | Threshold strategy | 0.2460 | 0.9749 | 0.5253 | 0.3451 | 0.2014 | 113125 | 0.0282 |
| Threshold = adaptive | Threshold strategy | 0.1591 | 0.9749 | 0.5253 | 0.2055 | 0.2884 | 113125 | 0.0282 |
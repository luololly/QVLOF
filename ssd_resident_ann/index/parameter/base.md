# Unified Evaluation and Parameter-Tuning Protocol

All methods are evaluated using an identical dataset, query set, ground truth, distance metric, and data type. The following resource constraints are also fixed across methods:

- **Thread count:** both index construction and query evaluation use 16 threads.
- **Construction memory budget:** every method receives an identical construction-memory limit. The selected limit must be sufficient for each index to complete construction as a single build process, without partitioning the dataset into independently built shards and subsequently merging them.
- **Search memory budget:** the search-time memory allowance is set to 30% of the corresponding dataset size. This allowance covers the in-memory search structures and runtime working memory used by each method.
- **Cache budget:** every method receives an identical cache capacity for a given dataset, so differences in Recall-QPS performance are not caused by unequal amounts of cached index data.

Within these fixed evaluation conditions, the key parameters that materially affect the Recall-QPS trade-off are tuned independently for each method. Semantically aligned basic parameters across methods use shared candidate ranges explored through grid search. Method-specific layout, routing, and filtering parameters use local search around their recommended or default settings. SPANN is tuned separately under its native parameterization.

The final reported result for each method is selected from its Recall-QPS Pareto frontier, prioritizing the configuration with the highest QPS around `Recall@10 = 0.9`.

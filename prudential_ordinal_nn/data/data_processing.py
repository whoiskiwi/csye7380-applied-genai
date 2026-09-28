import pandas as pd
from sklearn.model_selection import train_test_split

# 1. Load the training data
train = pd.read_csv("train.csv")
train = pd.read_csv("../data/train.csv")
test = pd.read_csv("../data/test.csv")
print("Response" in train.columns)   # True
print("Response" in test.columns)    # False
print(train.shape, test.shape)

# 2. Split 80% / 20%, stratified, fixed random seed
train_ids, val_ids = train_test_split(
    train["Id"],
    test_size=0.2,
    stratify=train["Response"],
    random_state=42
)

# 3. Tag each Id as belonging to train or val
split = pd.DataFrame({"Id": train["Id"]})
split["split"] = "train"
split.loc[split["Id"].isin(val_ids), "split"] = "val"

# 4. Save
split.to_csv("split_indices.csv", index=False)

# 5. Check the result
print(split.shape)
print(split["split"].value_counts())

merged = train.merge(split, on="Id")
print(merged.groupby("split")["Response"].value_counts(normalize=True).unstack().round(3))

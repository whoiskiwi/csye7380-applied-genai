"""
generate_data.py
================
Generates a SYNTHETIC gym-membership churn dataset with realistic, *designed*
relationships between the features and churn.

A gym member "churning" = cancelling their membership (leaving the service).
Because we design the causal structure ourselves, we know the ground-truth drivers
of churn (contract type, tenure, how often they actually visit, distance, ...).
That lets us later check whether the trained models "rediscover" those drivers.

Run:
    python generate_data.py

Output:
    data/gym_churn.csv   (6,000 members, ~27% churn)
"""

import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
OUT_CSV = os.path.join(DATA_DIR, "gym_churn.csv")

N_ROWS = 6000
RANDOM_STATE = 42


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def generate(n_rows: int = N_ROWS, seed: int = RANDOM_STATE) -> pd.DataFrame:
    """Build a synthetic gym-membership churn dataset and return it as a DataFrame."""
    rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------
    # 1. Raw features (drawn from plausible marginal distributions)
    # ------------------------------------------------------------------
    tenure = rng.integers(0, 73, size=n_rows)  # months as a member, 0-72

    contract_type = rng.choice(
        ["Month-to-month", "6-month", "Annual"],
        size=n_rows,
        p=[0.55, 0.25, 0.20],
    )

    # Monthly fee depends a bit on contract (longer commitments are discounted).
    base_fee = np.select(
        [contract_type == "Month-to-month", contract_type == "6-month",
         contract_type == "Annual"],
        [rng.normal(55, 10, n_rows), rng.normal(48, 8, n_rows),
         rng.normal(42, 8, n_rows)],
    )
    monthly_fee = np.clip(base_fee, 25, 90).round(2)

    # How engaged the member actually is (the strongest churn signal in gyms).
    avg_weekly_visits = np.clip(rng.normal(2.5, 1.3, n_rows), 0, 7).round(2)
    num_group_classes = rng.poisson(3, size=n_rows)          # classes attended / month
    distance_km = np.clip(rng.gamma(2.0, 4.0, n_rows), 0.3, 30).round(1)  # home -> gym
    extra_spending = np.clip(rng.gamma(1.5, 15, n_rows), 0, 200).round(2) # supplements/PT/merch

    age = rng.integers(18, 71, size=n_rows)
    personal_trainer = rng.choice(["Yes", "No"], size=n_rows, p=[0.3, 0.7])
    signup_promo = rng.choice(["Yes", "No"], size=n_rows, p=[0.4, 0.6])
    gender = rng.choice(["Female", "Male"], size=n_rows, p=[0.5, 0.5])

    total_paid = (np.maximum(tenure, 1) * monthly_fee
                  * rng.normal(1.0, 0.05, n_rows)).round(2)

    # ------------------------------------------------------------------
    # 2. DESIGNED churn model -> logit -> probability -> Bernoulli
    #    (these weights are the ground-truth drivers)
    # ------------------------------------------------------------------
    contract_effect = np.select(
        [contract_type == "Month-to-month", contract_type == "6-month",
         contract_type == "Annual"],
        [1.3, -0.2, -1.1],
    )
    trainer_effect = np.where(personal_trainer == "No", 0.4, 0.0)
    promo_effect = np.where(signup_promo == "Yes", 0.35, 0.0)  # promo members lapse after promo

    logit = (
        -0.08                                        # intercept -> ~27% base rate
        + contract_effect                            # month-to-month churn more
        - 0.030 * tenure                             # loyal (long tenure) churn less
        - 0.55 * avg_weekly_visits                   # disengagement is the top driver
        + 0.05 * distance_km                         # far from gym -> churn more
        + 0.010 * (monthly_fee - 45)                 # pricier plans churn a bit more
        - 0.04 * num_group_classes                   # class-goers stick around
        - 0.004 * extra_spending                     # invested members stay
        + trainer_effect                             # no trainer -> churn more
        + promo_effect                               # promo sign-ups lapse more
        + rng.normal(0, 0.35, n_rows)                # irreducible noise (keeps AUC realistic)
    )

    churn_prob = _sigmoid(logit)
    churn = rng.binomial(1, churn_prob)

    df = pd.DataFrame(
        {
            "tenure": tenure,
            "monthly_fee": monthly_fee,
            "total_paid": total_paid,
            "avg_weekly_visits": avg_weekly_visits,
            "num_group_classes": num_group_classes,
            "distance_km": distance_km,
            "extra_spending": extra_spending,
            "age": age,
            "contract_type": contract_type,
            "personal_trainer": personal_trainer,
            "signup_promo": signup_promo,
            "gender": gender,
            "Churn": churn.astype(int),
        }
    )
    return df


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    df = generate()
    df.to_csv(OUT_CSV, index=False)
    print(f"Wrote {OUT_CSV}")
    print(f"Shape: {df.shape}")
    print(f"Churn rate: {df['Churn'].mean():.1%}")
    print("\nHead:")
    print(df.head().to_string(index=False))


if __name__ == "__main__":
    main()

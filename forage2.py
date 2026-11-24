import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, recall_score, roc_auc_score, mean_squared_error
from xgboost import XGBClassifier
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import numpy as np
from math import log

df = pd.read_csv("C:/Users/Sachio/Downloads/Task 3 and 4_Loan_Data.csv", index_col='customer_id')
y = df['default']
X = df.drop(columns=['default'])

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=13, stratify=y)

# LogisticRegression is chosen because it gives the highest predictive accuracy and other metrics
clf = Pipeline([
    ("scaler", StandardScaler()),
    ("logreg", LogisticRegression(max_iter=1000))
])

clf.fit(X_train, y_train)

y_pred=clf.predict(X_test)
y_prob=clf.predict_proba(X_test)[:, 1]

print("\nMetrics")
print({
"Accuracy": clf.score(X_test, y_test),
"f1": f1_score(y_true=y_test, y_pred=y_pred),
"roc_auc": roc_auc_score(y_true=y_test, y_score=y_prob),
"recall": recall_score(y_true=y_test, y_pred=y_pred)
})
def loss_estimation (credit_lines_outstanding,
                     loan_amt_outstanding,
                     total_debt_outstanding,
                     income,
                     years_employed,
                     fico_score,
                     model= clf
                     ):
    pd_estimate = None
    loss_value = 0.0
    recovery_rate = 0.1
    loss_given_default = 1.0 - recovery_rate
    try:
        instance = pd.DataFrame([{
            "credit_lines_outstanding": credit_lines_outstanding,
            "loan_amt_outstanding": loan_amt_outstanding,
            "total_debt_outstanding": total_debt_outstanding,
            "income": income,
            "years_employed": years_employed,
            "fico_score": fico_score
        }])
        pd_estimate = model.predict_proba(instance)[0][1]

    except Exception as e:
        print(f"Error: {e}")

    if pd_estimate is None:
        return "sorry, default prob is none"
    
    loss_value = pd_estimate*loss_given_default*loan_amt_outstanding
    return {
        "Expected Loss": loss_value,
        "pd_estimate": pd_estimate
    }


def Bucket_FICO(n_buckets=10, data=df, model=clf):

    result = data.copy()

    result["default_prob"] = model.predict_proba(
        result.drop(columns=["default"])
    )[:, 1]

    result["rating"] = pd.qcut(
        result["fico_score"],
        q=n_buckets,
        labels=False
    )

    # reverse labels so high fico = low rating
    result["rating"] = (
        n_buckets - result["rating"]
    )

    summary = (
        result.groupby("rating")
        .agg(
            min_fico=("fico_score", "min"),
            max_fico=("fico_score", "max"),
            avg_pd=("default_prob", "mean"),
            borrowers=("fico_score", "count")
        )
        .sort_index()
    )

    return summary

print(Bucket_FICO())

def FICO_log ():
    x = df['default'].to_list()
    y = df['fico_score'].to_list()
    n = len(x)
    print (len(x), len(y))

    default = [0 for i in range(851)]
    total = [0 for i in range(851)]

    for i in range(n):
        y[i] = int(y[i])
        default[y[i]-300] += x[i]
        total[y[i]-300] += 1
        
    for i in range(0, 551):
        default[i] += default[i-1]
        total[i] += total[i-1]
        
    import numpy as np
        
    def log_likelihood(n, k):
        p = k/n
        if (p==0 or p==1):
            return 0
        return k*np.log(p)+ (n-k)*np.log(1-p)

    r = 10
    dp = [[[-10**18, 0] for i in range(551)] for j in range(r+1)]

    for i in range(r+1):
        for j in range(551):
            if (i==0):
                dp[i][j][0] = 0
            else:
                for k in range(j):
                    if (total[j]==total[k]):
                        continue
                    if (i==1):
                        dp[i][j][0] = log_likelihood(total[j], default[j])
                    else:
                        if (dp[i][j][0] < (dp[i-1][k][0] + log_likelihood(total[j]-total[k], default[j] - default[k]))):
                            dp[i][j][0] = log_likelihood(total[j]-total[k], default[j]-default[k]) + dp[i-1][k][0]
                            dp[i][j][1] = k
                                                        
    print (round(dp[r][550][0], 4))
                                                        
    k = 550
    l = []
    while r >= 0:
        l.append(k+300)
        k = dp[r][k][1]
        r -= 1

print(FICO_log())
from sklearn.preprocessing import OrdinalEncoder

severity_order = [['Low', 'Medium', 'High', 'Very High', 'Critical']]
oe = OrdinalEncoder(categories=severity_order)
df['severity_encoded'] = oe.fit_transform(df[['DEFECT_SEVERITY']])
# Low=0, Medium=1, High=2, Very High=3, Critical=4

# 'Automated' 和 'Automation' 明显是同一个东西 → 先合并
# 先归类再 One-Hot

test_type_map = {
    'Automated':    'Automation',   # 合并重复
    'Automation':   'Automation',
    'Manual':       'Manual',
    'Functional':   'Functional',
    'QA':           'Functional',   # QA归入Functional
    'Regression':   'Regression',
    'UAT':          'UAT',
    'SIT':          'SIT',
    'Performance':  'Performance',
    'Smoke':        'Smoke',
    'End to End':   'E2E',
    'DEV':          'Other',
    'SCS':          'Other',
    'CAV Suite':    'Other',
    'ORT':          'Other',
    'Resi':         'Other',
}
df['test_type_clean'] = df['DEFECT_TEST_TYPE'].map(test_type_map)
df = pd.get_dummies(df, columns=['test_type_clean'], drop_first=True)

# 太细了，直接One-Hot会产生40+列，噪音极大
# 必须归类到大环境

def map_environment(env):
    env = str(env).upper()
    if 'PROD' in env:       return 'PROD'      # PROD, PRE-PROD, PREPROD, POST-PROD
    elif 'UAT' in env:      return 'UAT'        # UAT, UAT2, UAT-A, UAT05
    elif 'QA' in env:       return 'QA'         # QA, QA1, QA2, QA01~06
    elif 'SIT' in env:      return 'SIT'        # SIT, SIT2
    elif 'INT' in env:      return 'INT'        # INT1, INT2, INT3
    elif 'DEV' in env:      return 'DEV'
    elif 'BETA' in env:     return 'BETA'
    else:                   return 'OTHER'

df['env_clean'] = df['DEFECT_ENVIRONMENT_DEFECT'].apply(map_environment)
df = pd.get_dummies(df, columns=['env_clean'], drop_first=True)

# 结果只有 7 列：PROD/UAT/QA/SIT/INT/DEV/BETA

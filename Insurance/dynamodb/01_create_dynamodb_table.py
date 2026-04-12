"""
Script: 01_create_dynamodb_table.py
Description: Creates a DynamoDB table for insurance claims and inserts 50 sample items.
Partition Key: ClaimID (String)
"""

import boto3
import json
import random
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

# ── Configuration ────────────────────────────────────────────────────────────
TABLE_NAME = "InsuranceClaims"
REGION     = "us-east-1"        # Change to your AWS region

# ── DynamoDB client ───────────────────────────────────────────────────────────

session = boto3.Session(profile_name="dev")

dynamodb = session.resource("dynamodb", region_name=REGION)
#client   = boto3.client("dynamodb", region_name=REGION)

# ── Seed for reproducibility ──────────────────────────────────────────────────
random.seed(42)

# ── Reference data pools ──────────────────────────────────────────────────────
POLICY_TYPES   = ["Automobile", "Home", "Health", "Life", "Travel", "Commercial"]
CLAIM_STATUSES = ["Submitted", "Under Review", "Approved", "Rejected", "Closed"]
PRIORITIES     = ["Low", "Medium", "High", "Critical"]

CLAIM_TYPES_BY_POLICY = {
    "Automobile": ["Collision", "Theft", "Vandalism", "Glass Damage", "Fire", "Flood Damage"],
    "Home":       ["Water Damage", "Fire", "Theft", "Storm Damage", "Structural Damage", "Vandalism"],
    "Health":     ["Hospitalization", "Surgery", "Emergency Room", "Prescription", "Rehabilitation", "Mental Health"],
    "Life":       ["Death Benefit", "Terminal Illness", "Accidental Death"],
    "Travel":     ["Trip Cancellation", "Medical Abroad", "Lost Luggage", "Flight Delay", "Emergency Evacuation"],
    "Commercial": ["Property Damage", "Liability", "Business Interruption", "Equipment Theft", "Cyber Incident"],
}

POLICY_HOLDERS = [
    ("John A. Doe",        "PHD-00101"), ("Alice P. Johnson",  "PHD-00102"),
    ("Robert M. Chen",     "PHD-00103"), ("Laura S. Martinez", "PHD-00104"),
    ("Michael B. Davis",   "PHD-00105"), ("Sarah K. Wilson",   "PHD-00106"),
    ("James T. Anderson",  "PHD-00107"), ("Emily R. Thompson", "PHD-00108"),
    ("Carlos G. Rivera",   "PHD-00109"), ("Megan L. Harris",   "PHD-00110"),
    ("David J. Clark",     "PHD-00111"), ("Jennifer N. Lewis",  "PHD-00112"),
    ("William E. Walker",  "PHD-00113"), ("Amanda C. Hall",    "PHD-00114"),
    ("Thomas P. Young",    "PHD-00115"), ("Patricia D. Allen",  "PHD-00116"),
    ("Christopher F. King","PHD-00117"), ("Stephanie H. Wright","PHD-00118"),
    ("Daniel R. Scott",    "PHD-00119"), ("Nicole M. Adams",   "PHD-00120"),
]

ADJUSTERS = [
    ("ADJ-0041", "Maria L. Torres"),
    ("ADJ-0042", "Kevin B. O'Brien"),
    ("ADJ-0043", "Linda F. Nguyen"),
    ("ADJ-0044", "Frank D. Patel"),
    ("ADJ-0045", "Susan Y. Kim"),
]

VEHICLE_MAKES = [
    ("Toyota",    "Camry",    ["2019","2020","2021","2022"]),
    ("Honda",     "Civic",    ["2018","2019","2020","2021"]),
    ("Ford",      "F-150",    ["2020","2021","2022","2023"]),
    ("Chevrolet", "Malibu",   ["2019","2020","2021"]),
    ("BMW",       "3 Series", ["2020","2021","2022"]),
    ("Tesla",     "Model 3",  ["2021","2022","2023"]),
    ("Nissan",    "Altima",   ["2019","2020","2021"]),
    ("Hyundai",   "Tucson",   ["2020","2021","2022"]),
]

STATES = [
    ("TX", "Austin"),     ("CA", "Los Angeles"), ("FL", "Miami"),
    ("NY", "New York"),   ("IL", "Chicago"),     ("AZ", "Phoenix"),
    ("WA", "Seattle"),    ("CO", "Denver"),      ("GA", "Atlanta"),
    ("NC", "Charlotte"),
]

INCIDENT_DESCRIPTIONS = {
    "Collision":             "Insured vehicle was involved in a collision. Damage to front and side panels.",
    "Theft":                 "Vehicle was stolen from the parking lot overnight. Police report filed.",
    "Vandalism":             "Vehicle windows smashed and exterior keyed while parked on the street.",
    "Glass Damage":          "Windshield cracked by road debris on the highway.",
    "Fire":                  "Engine fire triggered by electrical fault. Vehicle declared total loss.",
    "Flood Damage":          "Vehicle submerged during flash flood event. Water damage to interior.",
    "Water Damage":          "Burst pipe in the kitchen caused significant flooding to the ground floor.",
    "Storm Damage":          "Roof damaged by hailstorm. Multiple windows broken.",
    "Structural Damage":     "Foundation cracks detected following seismic activity.",
    "Hospitalization":       "Claimant admitted to hospital for emergency treatment. 5-day stay.",
    "Surgery":               "Scheduled orthopedic surgery. Pre-authorization confirmed.",
    "Emergency Room":        "Claimant treated in ER following an accident. X-rays and stitches required.",
    "Prescription":          "Monthly prescription for chronic condition. Claim for medication costs.",
    "Rehabilitation":        "Post-surgery physical therapy sessions over 6 weeks.",
    "Mental Health":         "Outpatient mental health treatment. 10 sessions with licensed therapist.",
    "Death Benefit":         "Policy holder deceased. Death certificate and beneficiary docs submitted.",
    "Terminal Illness":      "Claimant diagnosed with terminal condition. Accelerated benefit requested.",
    "Accidental Death":      "Accidental death confirmed by coroner. Police and medical reports attached.",
    "Trip Cancellation":     "Flight cancelled due to severe weather. Hotel and ticket costs claimed.",
    "Medical Abroad":        "Claimant required hospitalization during international travel.",
    "Lost Luggage":          "Luggage lost by airline during international travel. Contents valued.",
    "Flight Delay":          "Flight delayed over 12 hours. Meal and accommodation costs claimed.",
    "Emergency Evacuation":  "Medical evacuation required from remote location.",
    "Property Damage":       "Commercial property damaged by fire in adjacent unit.",
    "Liability":             "Third party injured on business premises. Legal notice received.",
    "Business Interruption": "Operations halted for 10 days following flooding. Revenue loss claimed.",
    "Equipment Theft":       "Business equipment stolen from warehouse. Inventory list attached.",
    "Cyber Incident":        "Ransomware attack encrypted business data. Recovery costs claimed.",
}

DOC_TYPES_BY_POLICY = {
    "Automobile": ["PoliceReport", "DamagePhoto", "RepairEstimate", "DriverLicense"],
    "Home":       ["PropertyPhoto", "RepairEstimate", "PoliceReport", "HomeInspection"],
    "Health":     ["MedicalReport", "HospitalInvoice", "DoctorPrescription"],
    "Life":       ["DeathCertificate", "BeneficiaryForm", "PolicyDocument"],
    "Travel":     ["FlightTicket", "HotelReceipt", "MedicalReport", "PoliceReport"],
    "Commercial": ["IncidentReport", "PropertyPhoto", "FinancialStatement", "LegalNotice"],
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def random_date(start_days_ago=365, end_days_ago=1) -> str:
    delta = random.randint(end_days_ago, start_days_ago)
    return (datetime.utcnow() - timedelta(days=delta)).strftime("%Y-%m-%d")


def random_amount(min_usd=500, max_usd=80000) -> int:
    """Returns amount in cents."""
    return random.randint(min_usd, max_usd) * 100


def build_claim(index: int) -> dict:
    """Generate one realistic insurance claim item."""
    claim_id      = f"CLM-2024-{index:06d}"
    policy_type   = random.choice(POLICY_TYPES)
    claim_type    = random.choice(CLAIM_TYPES_BY_POLICY[policy_type])
    status        = random.choice(CLAIM_STATUSES)
    priority      = random.choice(PRIORITIES)
    holder_name, holder_id = random.choice(POLICY_HOLDERS)
    adj_id, adj_name       = random.choice(ADJUSTERS)
    state_code, city       = random.choice(STATES)
    street_num    = random.randint(100, 9999)
    incident_date = random_date(370, 5)
    claim_date    = (
        datetime.strptime(incident_date, "%Y-%m-%d") + timedelta(days=random.randint(1, 3))
    ).strftime("%Y-%m-%d")
    claimed_amt   = random_amount(500, 75000)
    deductible    = random.choice([25000, 50000, 100000, 150000])   # in cents
    approved_amt  = claimed_amt - deductible if status == "Approved" else 0

    description = INCIDENT_DESCRIPTIONS.get(
        claim_type, f"Incident of type '{claim_type}' reported by policy holder."
    )
    doc_types = DOC_TYPES_BY_POLICY.get(policy_type, ["IncidentReport", "Photo"])
    documents = [
        {"DocType": dt, "S3Key": f"claims/{claim_id}/{dt.lower()}.pdf"}
        for dt in random.sample(doc_types, k=min(len(doc_types), random.randint(1, 3)))
    ]

    item = {
        # ── Primary Key ──────────────────────────────────────────────────
        "ClaimID":             claim_id,

        # ── Policy ──────────────────────────────────────────────────────
        "PolicyNumber":        f"POL-{random.randint(10000000, 99999999)}",
        "PolicyType":          policy_type,
        "PolicyHolderName":    holder_name,
        "PolicyHolderID":      holder_id,

        # ── Claim details ────────────────────────────────────────────────
        "ClaimType":           claim_type,
        "ClaimStatus":         status,
        "ClaimDate":           claim_date,
        "IncidentDate":        incident_date,
        "IncidentLocation":    f"{street_num} {'Main' if index % 2 == 0 else 'Oak'} St, {city}, {state_code}",
        "IncidentDescription": description,

        # ── Financial ────────────────────────────────────────────────────
        "ClaimedAmount":       claimed_amt,
        "ApprovedAmount":      approved_amt,
        "Deductible":          deductible,
        "Currency":            "USD",

        # ── Adjuster ─────────────────────────────────────────────────────
        "AssignedAdjusterID":   adj_id,
        "AssignedAdjusterName": adj_name,
        "Priority":             priority,
        "EstimatedResolutionDate": (
            datetime.strptime(claim_date, "%Y-%m-%d") + timedelta(days=random.randint(10, 45))
        ).strftime("%Y-%m-%d"),

        # ── Documents ────────────────────────────────────────────────────
        "Documents": documents,

        # ── Audit ────────────────────────────────────────────────────────
        "CreatedAt":  datetime.utcnow().isoformat() + "Z",
        "UpdatedAt":  datetime.utcnow().isoformat() + "Z",
        "CreatedBy":  random.choice(["portal-web", "mobile-app", "agent-portal", "api"]),
        "Notes":      f"Auto-generated sample record #{index}.",
    }

    # ── Policy-type-specific extra fields ────────────────────────────────
    if policy_type == "Automobile":
        make, model, years = random.choice(VEHICLE_MAKES)
        item["VehicleDetails"] = {
            "VIN":          f"1{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{random.randint(10000000, 99999999):08d}",
            "Make":         make,
            "Model":        model,
            "Year":         random.choice(years),
            "LicensePlate": f"{state_code}-{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{random.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{random.randint(1000, 9999)}",
            "Mileage":      random.randint(5000, 120000),
        }
        if random.random() > 0.4:
            item["ThirdPartyInvolved"] = True
            item["ThirdPartyDetails"] = {
                "Name":             f"Third Party #{random.randint(100, 999)}",
                "ContactPhone":     f"+1-{random.randint(200, 999)}-555-{random.randint(1000, 9999)}",
                "InsuranceCompany": random.choice(["AllState", "StateFarm", "GEICO", "Progressive", "Nationwide"]),
                "PolicyNumber":     f"TP-{random.randint(10000000, 99999999)}",
            }
        else:
            item["ThirdPartyInvolved"] = False

    elif policy_type == "Home":
        item["PropertyDetails"] = {
            "PropertyType":     random.choice(["Single Family", "Condo", "Townhouse", "Multi-Family"]),
            "ConstructionYear": str(random.randint(1970, 2020)),
            "SquareFootage":    random.randint(800, 4500),
            "Address":          item["IncidentLocation"],
        }

    elif policy_type == "Health":
        item["MedicalDetails"] = {
            "DiagnosisCode":    f"ICD-{random.randint(100, 999)}.{random.randint(0, 9)}",
            "HospitalName":     random.choice(["General Hospital", "St. Mary's Medical", "City Health Center", "Memorial Hospital"]),
            "TreatingPhysician": f"Dr. {random.choice(['Smith','Jones','Patel','Kim','Garcia'])}",
            "AdmissionDate":    incident_date,
            "DischargeDate":    (
                datetime.strptime(incident_date, "%Y-%m-%d") + timedelta(days=random.randint(1, 10))
            ).strftime("%Y-%m-%d"),
        }

    return item


# ── Table creation ────────────────────────────────────────────────────────────
def create_table():
    """Create the InsuranceClaims DynamoDB table."""
    print(f"Creating table '{TABLE_NAME}'...")
    try:
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "ClaimID", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "ClaimID", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
            Tags=[
                {"Key": "Project",     "Value": "InsuranceDemo"},
                {"Key": "Environment", "Value": "Dev"},
            ]
        )
        print("Waiting for table to become ACTIVE...")
        table.wait_until_exists()
        print(f"✅  Table '{TABLE_NAME}' created successfully.")
        return table

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"ℹ️  Table '{TABLE_NAME}' already exists. Skipping creation.")
            return dynamodb.Table(TABLE_NAME)
        else:
            raise


# ── Batch insert 50 items ─────────────────────────────────────────────────────
def insert_sample_items(table, count=50):
    """Insert `count` sample insurance claims using batch_writer (max 25/batch)."""
    print(f"\nInserting {count} sample claims...")

    items = [build_claim(i + 1) for i in range(count)]

    # batch_writer automatically groups writes in batches of 25 (DynamoDB limit)
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)

    # ── Summary ───────────────────────────────────────────────────────────
    status_counts = {}
    type_counts   = {}
    for item in items:
        s = item["ClaimStatus"]
        p = item["PolicyType"]
        status_counts[s] = status_counts.get(s, 0) + 1
        type_counts[p]   = type_counts.get(p, 0) + 1

    print(f"\n✅  {count} items inserted successfully.")
    print("\n📊  Distribution by ClaimStatus:")
    for status, cnt in sorted(status_counts.items()):
        print(f"     {status:<22} {cnt:>3} items")
    print("\n📊  Distribution by PolicyType:")
    for ptype, cnt in sorted(type_counts.items()):
        print(f"     {ptype:<22} {cnt:>3} items")
    print(f"\n🔑  ClaimIDs: CLM-2024-000001 → CLM-2024-{count:06d}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    table = create_table()
    insert_sample_items(table, count=50)
    print("\n✅  Setup complete.")

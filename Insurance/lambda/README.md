# AWS Insurance Claims – Scripts & Lambda Functions

## 📁 Files

| File | Description |
|------|-------------|
| `01_create_dynamodb_table.py` | Script local: crea la tabla DynamoDB e inserta un ítem de ejemplo |
| `02_lambda_insert_claim.py`   | Lambda: inserta un nuevo reclamo en DynamoDB |
| `03_lambda_get_claims.py`     | Lambda: recupera todos los reclamos (con filtros y paginación) |
| `04_lambda_bedrock_claims.py` | Lambda: analiza un reclamo con Amazon Bedrock (Claude 3 Sonnet) |

---

## 1️⃣ Crear la tabla DynamoDB

### Prerrequisitos
```bash
pip install boto3
aws configure   # o configura las variables AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
```

### Ejecutar
```bash
python 01_create_dynamodb_table.py
```

Esto crea la tabla `InsuranceClaims` con **Partition Key = ClaimID** (billing: on-demand)
e inserta un ítem de ejemplo con los atributos de un reclamo de automóvil.

---

## 2️⃣ Lambda – Insertar un reclamo

### Despliegue
1. En AWS Console → Lambda → **Create function** → Author from scratch
2. Runtime: **Python 3.12**
3. Sube (o pega) el contenido de `02_lambda_insert_claim.py`
4. Handler: `02_lambda_insert_claim.lambda_handler`

### Variables de entorno
| Variable    | Valor por defecto |
|-------------|-------------------|
| `TABLE_NAME` | `InsuranceClaims` |
| `REGION`     | `us-east-1`       |

### IAM Permissions (adjuntar a la Lambda Role)
```json
{
  "Effect": "Allow",
  "Action": ["dynamodb:PutItem"],
  "Resource": "arn:aws:dynamodb:*:*:table/InsuranceClaims"
}
```

### Payload de prueba
```json
{
  "PolicyNumber":     "POL-11112222",
  "PolicyType":       "Home",
  "PolicyHolderName": "Alice P. Johnson",
  "ClaimType":        "Water Damage",
  "ClaimDate":        "2024-11-20",
  "IncidentDate":     "2024-11-19",
  "IncidentLocation": "456 Oak Ave, Dallas, TX 75201",
  "IncidentDescription": "Burst pipe in the kitchen caused flooding.",
  "ClaimedAmount":    800000,
  "Deductible":       100000,
  "Currency":         "USD",
  "Priority":         "High"
}
```

---

## 3️⃣ Lambda – Recuperar reclamos

### Despliegue
Mismo proceso que la Lambda anterior.
Handler: `03_lambda_get_claims.lambda_handler`

### IAM Permissions
```json
{
  "Effect": "Allow",
  "Action": ["dynamodb:Scan", "dynamodb:GetItem"],
  "Resource": "arn:aws:dynamodb:*:*:table/InsuranceClaims"
}
```

### Query parameters disponibles
| Parámetro    | Descripción                                  |
|--------------|----------------------------------------------|
| `claimId`    | Obtiene un único reclamo por ID (GetItem)    |
| `status`     | Filtra por ClaimStatus (`Approved`, etc.)    |
| `policyType` | Filtra por PolicyType (`Automobile`, etc.)   |
| `priority`   | Filtra por Priority (`High`, etc.)           |
| `limit`      | Número máximo de ítems por página (max 100)  |
| `lastKey`    | Token de paginación de la página anterior    |

### Payloads de prueba

**Todos los reclamos:**
```json
{}
```

**Un reclamo específico:**
```json
{ "claimId": "CLM-2024-000123" }
```

**Filtrar por estado:**
```json
{ "queryStringParameters": { "status": "Under Review" } }
```

---

## 4️⃣ Lambda – Amazon Bedrock (análisis con IA)

### Prerrequisito – Activar el modelo
1. AWS Console → **Amazon Bedrock** → Model access
2. Solicitar acceso a **Anthropic Claude 3 Sonnet**

### Despliegue
Handler: `04_lambda_bedrock_claims.lambda_handler`

### Variables de entorno
| Variable    | Valor por defecto                              |
|-------------|------------------------------------------------|
| `REGION`    | `us-east-1`                                    |
| `MODEL_ID`  | `anthropic.claude-3-sonnet-20240229-v1:0`      |
| `TABLE_NAME`| `InsuranceClaims`                              |
| `MAX_TOKENS`| `1024`                                         |

### IAM Permissions
```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "dynamodb:GetItem"
  ],
  "Resource": "*"
}
```

### Payload de prueba – por ClaimID (fetches from DynamoDB)
```json
{ "claimId": "CLM-2024-000123" }
```

### Payload de prueba – con datos inline
```json
{
  "claim": {
    "ClaimID": "CLM-TEST-001",
    "PolicyType": "Automobile",
    "PolicyHolderName": "John Doe",
    "ClaimType": "Collision",
    "ClaimDate": "2024-11-15",
    "IncidentDate": "2024-11-14",
    "ClaimedAmount": 1250000,
    "Deductible": 50000,
    "IncidentDescription": "Rear-end collision at traffic light.",
    "ThirdPartyInvolved": true
  }
}
```

### Respuesta esperada
```json
{
  "ClaimID": "CLM-2024-000123",
  "analysis": {
    "summary": "The insured vehicle was involved in a rear-end collision...",
    "riskLevel": "Medium",
    "fraudSignals": [],
    "recommendedAction": "Approve with investigation",
    "estimatedPayout": 11500.00,
    "reasoning": "No major fraud signals detected. Damage consistent with description."
  },
  "model": "anthropic.claude-3-sonnet-20240229-v1:0",
  "inputTokens": 380,
  "outputTokens": 210
}
```

---

## 🗂️ DynamoDB – Atributos del ítem de ejemplo

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `ClaimID` | String | **Partition Key** – Identificador único del reclamo |
| `PolicyNumber` | String | Número de póliza |
| `PolicyType` | String | Tipo: Automobile, Home, Health, Life |
| `PolicyHolderName` | String | Nombre del asegurado |
| `ClaimType` | String | Tipo de siniestro |
| `ClaimStatus` | String | Estado: Submitted, Under Review, Approved, Rejected, Closed |
| `ClaimDate` | String | Fecha de presentación del reclamo |
| `IncidentDate` | String | Fecha del incidente |
| `IncidentLocation` | String | Dirección del incidente |
| `IncidentDescription` | String | Descripción del siniestro |
| `ClaimedAmount` | Number | Monto reclamado (en centavos) |
| `ApprovedAmount` | Number | Monto aprobado (en centavos) |
| `Deductible` | Number | Deducible (en centavos) |
| `Currency` | String | Moneda (USD) |
| `VehicleDetails` | Map | VIN, Make, Model, Year, LicensePlate, Mileage |
| `ThirdPartyInvolved` | Boolean | ¿Hay terceros involucrados? |
| `ThirdPartyDetails` | Map | Datos del tercero |
| `AssignedAdjusterID` | String | ID del ajustador asignado |
| `Priority` | String | Prioridad: Low, Medium, High, Critical |
| `Documents` | List | Lista de documentos en S3 |
| `CreatedAt` | String | Timestamp ISO 8601 de creación |
| `UpdatedAt` | String | Timestamp ISO 8601 de última actualización |

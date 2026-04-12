# Academia Cloud & IA – Eventos de prueba para las funciones Lambda

## Despliegue

```bash
aws cloudformation deploy \
  --template-file academia-cloud-ia.yaml \
  --stack-name academia-cloud-ia \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides Environment=dev
```

---

## getCourses – Eventos de prueba

### 1. Obtener TODOS los cursos
```json
{
  "queryStringParameters": null
}
```

### 2. Filtrar por categoría
```json
{
  "queryStringParameters": {
    "category": "cloud"
  }
}
```
> Categorías disponibles: `cloud` · `ia` · `devops` · `security` · `data`

### 3. Solo cursos activos de una categoría
```json
{
  "queryStringParameters": {
    "category": "ia",
    "active": "true"
  }
}
```

### 4. Obtener un curso concreto (GetItem)
```json
{
  "queryStringParameters": {
    "courseId": "AWS-001",
    "category": "cloud"
  }
}
```

---

## insertCourse – Evento de prueba completo

```json
{
  "body": "{\"courseId\":\"AWS-010\",\"category\":\"cloud\",\"title\":\"AWS Advanced Networking Specialty\",\"provider\":\"Amazon Web Services\",\"level\":\"advanced\",\"durationHours\":45,\"price\":329.00,\"currency\":\"EUR\",\"language\":\"es\",\"tags\":[\"aws\",\"networking\",\"vpc\",\"direct-connect\",\"transit-gateway\"],\"description\":\"Diseño y gestión de redes avanzadas en AWS: VPC, Direct Connect, Transit Gateway y Route 53.\",\"rating\":0.0,\"enrollments\":0,\"active\":true}"
}
```

### Mismo evento con el body ya como objeto (invocación directa, sin API Gateway)
```json
{
  "body": {
    "courseId": "AWS-010",
    "category": "cloud",
    "title": "AWS Advanced Networking Specialty",
    "provider": "Amazon Web Services",
    "level": "advanced",
    "durationHours": 45,
    "price": 329.00,
    "currency": "EUR",
    "language": "es",
    "tags": ["aws", "networking", "vpc", "direct-connect", "transit-gateway"],
    "description": "Diseño y gestión de redes avanzadas en AWS: VPC, Direct Connect, Transit Gateway y Route 53.",
    "rating": 0.0,
    "enrollments": 0,
    "active": true
  }
}
```

---

## Campos del item de curso

| Campo           | Tipo    | Obligatorio | Descripción                                  |
|-----------------|---------|-------------|----------------------------------------------|
| courseId        | String  | ✅          | Clave única. Formato: `PREFIJO-NNN`          |
| category        | String  | ✅          | `cloud` · `ia` · `devops` · `security` · `data` |
| title           | String  | ✅          | Nombre del curso                             |
| level           | String  | ✅          | `beginner` · `intermediate` · `advanced`     |
| durationHours   | Number  | ✅          | Duración en horas (> 0)                      |
| price           | Number  | ✅          | Precio en la moneda indicada (>= 0)          |
| provider        | String  | ❌          | Empresa o academia que imparte el curso      |
| currency        | String  | ❌          | Por defecto `EUR`                            |
| language        | String  | ❌          | Por defecto `es`                             |
| tags            | List    | ❌          | Etiquetas de búsqueda                        |
| description     | String  | ❌          | Descripción del curso                        |
| rating          | Number  | ❌          | Valoración media (0.0 – 5.0)                |
| enrollments     | Number  | ❌          | Número de alumnos matriculados               |
| active          | Boolean | ❌          | Por defecto `true`                           |
| createdAt       | String  | —           | ISO 8601. Lo asigna automáticamente Lambda   |

---

## Respuestas esperadas

### getCourses – 200 OK (lista)
```json
{
  "statusCode": 200,
  "body": {
    "count": 5,
    "courses": [ { "courseId": "AWS-001", "category": "cloud", "..." } ]
  }
}
```

### insertCourse – 201 Created
```json
{
  "statusCode": 201,
  "body": {
    "message": "Curso insertado correctamente",
    "courseId": "AWS-010",
    "category": "cloud"
  }
}
```

### insertCourse – 400 Bad Request (validación)
```json
{
  "statusCode": 400,
  "body": {
    "message": "Faltan campos obligatorios",
    "missing": ["title", "level"]
  }
}
```

---

## Invocar desde CLI

```bash
# getCourses – todos
aws lambda invoke \
  --function-name getCourses-dev \
  --payload '{"queryStringParameters":null}' \
  --cli-binary-format raw-in-base64-out \
  response.json && cat response.json

# getCourses – por categoría
aws lambda invoke \
  --function-name getCourses-dev \
  --payload '{"queryStringParameters":{"category":"ia"}}' \
  --cli-binary-format raw-in-base64-out \
  response.json && cat response.json

# insertCourse
aws lambda invoke \
  --function-name insertCourse-dev \
  --payload '{"body":{"courseId":"TEST-001","category":"devops","title":"Curso de prueba","level":"beginner","durationHours":10,"price":99.00}}' \
  --cli-binary-format raw-in-base64-out \
  response.json && cat response.json
```

CREATE TABLE sample_entity_status(
    id		                        SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO sample_entity_status (enumerator) VALUES
('created'),
('pending'),
('success'),
('failed');

CREATE TABLE sample_entity(
    id                              SERIAL PRIMARY KEY,
    sample_entity_key               CHAR(36) NOT NULL,
    status_id                       INTEGER NOT NULL REFERENCES sample_entity_status(id),
    sample_entity_data              JSONB NOT NULL,
    name                            VARCHAR(255) NOT NULL,
    email                           VARCHAR(255) NOT NULL,
    document_number                 CHAR(14) NOT NULL,
    birthdate                       DATE NOT NULL,
    counter                         INTEGER NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(sample_entity_key),
    UNIQUE(document_number),
    UNIQUE(email)
);

CREATE TABLE sample_entity_status_event(
    id                              SERIAL PRIMARY KEY,
    sample_entity_id                INTEGER NOT NULL REFERENCES sample_entity(id),
    status_id                       INTEGER NOT NULL REFERENCES sample_entity_status(id),
    event_datetime                  TIMESTAMP NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE customer_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    description                     VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

INSERT INTO customer_status (enumerator, description) VALUES
('created', 'Cadastro recebido, aguardando início de validações'),
('kyc_pending', 'Validações cadastrais e antifraude em andamento'),
('under_review', 'Cadastro sob análise manual de compliance'),
('active', 'Cadastro aprovado e contas ativas'),
('rejected', 'Cadastro recusado por fraude ou inconsistência grave'),
('blocked', 'Cadastro bloqueado cautelarmente por conformidade')
ON CONFLICT (enumerator) DO NOTHING;

CREATE TABLE customer(
    id                              SERIAL PRIMARY KEY,
    customer_key                    CHAR(36) NOT NULL UNIQUE,
    status_id                       INTEGER NOT NULL REFERENCES customer_status(id),
    name                            VARCHAR(255) NOT NULL,
    legal_name                      VARCHAR(255) NOT NULL,
    email                           VARCHAR(255) NOT NULL UNIQUE,
    cpf                             CHAR(14) NOT NULL UNIQUE,
    cnpj                            CHAR(18) NOT NULL UNIQUE,
    birthdate                       DATE NOT NULL,
    phone                           VARCHAR(20) NOT NULL,
    password_hash                   VARCHAR(255) NOT NULL,
    pin_hash                        VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    updated_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE customer_status_event(
    id                              SERIAL PRIMARY KEY,
    customer_id                     INTEGER NOT NULL REFERENCES customer(id),
    from_status_id                  INTEGER REFERENCES customer_status(id),
    to_status_id                    INTEGER NOT NULL REFERENCES customer_status(id),
    reason_code                     VARCHAR(100) NOT NULL,
    reason_detail                   JSONB,
    event_datetime                  TIMESTAMP NOT NULL DEFAULT(NOW()),
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);
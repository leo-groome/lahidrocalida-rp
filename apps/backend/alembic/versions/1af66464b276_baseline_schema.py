"""baseline schema (espejo exacto de produccion, generado via pg_dump --schema-only)

Revision ID: 1af66464b276
Revises:
Create Date: 2026-08-24 12:42:12.798788

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1af66464b276"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BASELINE_DDL = """

CREATE TYPE public.metodo_pago_gasto_enum AS ENUM (
    'efectivo',
    'tarjeta'
);

CREATE TYPE public.tipo_gasto_enum AS ENUM (
    'directo',
    'indirecto',
    'nomina'
);

CREATE FUNCTION public.show_db_tree() RETURNS TABLE(tree_structure text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- First show all databases
    RETURN QUERY
    SELECT ':file_folder: ' || datname || ' (DATABASE)'
    FROM pg_database 
    WHERE datistemplate = false;

    -- Then show current database structure
    RETURN QUERY
    WITH RECURSIVE 
    -- Get schemas
    schemas AS (
        SELECT 
            n.nspname AS object_name,
            1 AS level,
            n.nspname AS path,
            'SCHEMA' AS object_type
        FROM pg_namespace n
        WHERE n.nspname NOT LIKE 'pg_%' 
        AND n.nspname != 'information_schema'
    ),

    -- Get all objects (tables, views, functions, etc.)
    objects AS (
        SELECT 
            c.relname AS object_name,
            2 AS level,
            s.path || ' → ' || c.relname AS path,
            CASE c.relkind
                WHEN 'r' THEN 'TABLE'
                WHEN 'v' THEN 'VIEW'
                WHEN 'm' THEN 'MATERIALIZED VIEW'
                WHEN 'i' THEN 'INDEX'
                WHEN 'S' THEN 'SEQUENCE'
                WHEN 'f' THEN 'FOREIGN TABLE'
            END AS object_type
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN schemas s ON n.nspname = s.object_name
        WHERE c.relkind IN ('r','v','m','i','S','f')

        UNION ALL

        SELECT 
            p.proname AS object_name,
            2 AS level,
            s.path || ' → ' || p.proname AS path,
            'FUNCTION' AS object_type
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        JOIN schemas s ON n.nspname = s.object_name
    ),

    -- Combine schemas and objects
    combined AS (
        SELECT * FROM schemas
        UNION ALL
        SELECT * FROM objects
    )

    -- Final output with tree-like formatting
    SELECT 
        REPEAT('    ', level) || 
        CASE 
            WHEN level = 1 THEN '└── :open_file_folder: '
            ELSE '    └── ' || 
                CASE object_type
                    WHEN 'TABLE' THEN ':bar_chart: '
                    WHEN 'VIEW' THEN ':eye: '
                    WHEN 'MATERIALIZED VIEW' THEN ':newspaper: '
                    WHEN 'FUNCTION' THEN ':zap: '
                    WHEN 'INDEX' THEN ':mag: '
                    WHEN 'SEQUENCE' THEN ':1234: '
                    WHEN 'FOREIGN TABLE' THEN ':globe_with_meridians: '
                    ELSE ''
                END
        END || object_name || ' (' || object_type || ')'
    FROM combined
    ORDER BY path;
END;
$$;


CREATE TABLE public.articulos (
    id integer NOT NULL,
    nombre character varying(150) NOT NULL,
    unidad character varying(20) NOT NULL,
    costo_estandar numeric(10,2) NOT NULL,
    categoria_id integer NOT NULL
);

CREATE SEQUENCE public.articulos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.articulos_id_seq OWNED BY public.articulos.id;

CREATE TABLE public.articulos_pedido (
    id integer NOT NULL,
    pedido_id integer NOT NULL,
    platillo_id integer NOT NULL,
    cantidad integer NOT NULL,
    precio_cobrado numeric(8,2) NOT NULL,
    modificaciones text,
    estado_item character varying(20) DEFAULT 'pendiente'::character varying,
    client_request_id character varying(36)
);

CREATE SEQUENCE public.articulos_pedido_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.articulos_pedido_id_seq OWNED BY public.articulos_pedido.id;

CREATE TABLE public.categorias_articulo (
    id integer NOT NULL,
    nombre character varying(80) NOT NULL
);

CREATE SEQUENCE public.categorias_articulo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.categorias_articulo_id_seq OWNED BY public.categorias_articulo.id;

CREATE TABLE public.gasto_detalles (
    id integer NOT NULL,
    gasto_id integer,
    articulo_id integer NOT NULL,
    cantidad numeric(10,2) NOT NULL,
    precio_unitario numeric(10,2) NOT NULL,
    subtotal_linea numeric(10,2) NOT NULL
);

CREATE SEQUENCE public.gasto_detalles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.gasto_detalles_id_seq OWNED BY public.gasto_detalles.id;

CREATE TABLE public.gastos (
    id integer NOT NULL,
    proveedor_id integer,
    tipo_gasto public.tipo_gasto_enum NOT NULL,
    metodo_pago public.metodo_pago_gasto_enum NOT NULL,
    descripcion character varying(255),
    folio character varying(100),
    subtotal numeric(10,2) NOT NULL,
    total numeric(10,2) NOT NULL,
    total_manual numeric(10,2),
    fecha_gasto timestamp with time zone,
    notas text,
    sucursal_id integer,
    turno_id integer
);

CREATE SEQUENCE public.gastos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.gastos_id_seq OWNED BY public.gastos.id;

CREATE TABLE public.nomina_detalles (
    id integer NOT NULL,
    gasto_id integer NOT NULL,
    usuario_id integer NOT NULL,
    monto numeric(10,2) NOT NULL,
    notas text
);

CREATE SEQUENCE public.nomina_detalles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.nomina_detalles_id_seq OWNED BY public.nomina_detalles.id;

CREATE TABLE public.pedidos (
    id integer NOT NULL,
    numero_display character varying(10) NOT NULL,
    nombre_cliente character varying(100),
    total numeric(8,2) NOT NULL,
    estado character varying(20),
    metodo_pago character varying(20),
    tipo_orden character varying(20),
    fecha_creacion timestamp with time zone,
    sucursal_id integer,
    usuario_id integer,
    mesa character varying(10),
    propina_efectivo numeric(8,2) DEFAULT 0,
    propina_tarjeta numeric(8,2) DEFAULT 0,
    fecha_pago timestamp with time zone,
    turno_id integer,
    client_request_id character varying(36),
    parent_pedido_id integer
);

CREATE SEQUENCE public.pedidos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.pedidos_id_seq OWNED BY public.pedidos.id;

CREATE TABLE public.platillos (
    id integer NOT NULL,
    nombre character varying(100) NOT NULL,
    descripcion text,
    precio numeric(8,2) NOT NULL,
    categoria character varying(50) NOT NULL,
    estado character varying(20),
    kds_name character varying(32)
);

CREATE SEQUENCE public.platillos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.platillos_id_seq OWNED BY public.platillos.id;

CREATE TABLE public.proveedores (
    id integer NOT NULL,
    nombre character varying(150) NOT NULL,
    telefono character varying(50),
    direccion text,
    notas text,
    sucursal_id integer
);

CREATE SEQUENCE public.proveedores_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.proveedores_id_seq OWNED BY public.proveedores.id;

CREATE TABLE public.registros_asistencia (
    id integer NOT NULL,
    usuario_id integer NOT NULL,
    fecha_entrada timestamp with time zone NOT NULL,
    fecha_salida timestamp with time zone,
    notas text
);

CREATE SEQUENCE public.registros_asistencia_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.registros_asistencia_id_seq OWNED BY public.registros_asistencia.id;

CREATE TABLE public.sucursales (
    id integer NOT NULL,
    nombre character varying(100) NOT NULL,
    direccion text
);

CREATE SEQUENCE public.sucursales_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.sucursales_id_seq OWNED BY public.sucursales.id;

CREATE TABLE public.turno_denominaciones (
    id integer NOT NULL,
    turno_id integer NOT NULL,
    tipo character varying(10) NOT NULL,
    denominacion integer NOT NULL,
    cantidad integer NOT NULL,
    subtotal numeric(10,2) NOT NULL,
    CONSTRAINT chk_turno_denominacion_cantidad CHECK ((cantidad >= 0)),
    CONSTRAINT chk_turno_denominacion_subtotal CHECK ((subtotal >= (0)::numeric)),
    CONSTRAINT chk_turno_denominacion_tipo CHECK (((tipo)::text = ANY ((ARRAY['inicial'::character varying, 'final'::character varying])::text[]))),
    CONSTRAINT chk_turno_denominacion_valor CHECK ((denominacion = ANY (ARRAY[1000, 500, 200, 100, 50, 20, 10, 5, 2, 1])))
);

CREATE SEQUENCE public.turno_denominaciones_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.turno_denominaciones_id_seq OWNED BY public.turno_denominaciones.id;

CREATE TABLE public.turnos (
    id integer NOT NULL,
    sucursal_id integer NOT NULL,
    usuario_id integer NOT NULL,
    fecha_apertura timestamp with time zone,
    fecha_cierre timestamp with time zone,
    estado character varying(10) NOT NULL,
    total_inicial numeric(10,2) NOT NULL,
    total_final numeric(10,2),
    ventas_efectivo numeric(10,2),
    propinas_efectivo numeric(10,2),
    diferencia numeric(10,2),
    observaciones text,
    monto_retirado numeric(10,2),
    monto_restante_en_caja numeric(10,2),
    CONSTRAINT chk_turno_estado CHECK (((estado)::text = ANY ((ARRAY['abierto'::character varying, 'cerrado'::character varying])::text[])))
);

CREATE SEQUENCE public.turnos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.turnos_id_seq OWNED BY public.turnos.id;

CREATE TABLE public.usuarios (
    id integer NOT NULL,
    nombre character varying(100) NOT NULL,
    rol character varying(20) NOT NULL,
    activo boolean,
    sucursal_id integer,
    permiso_registros boolean DEFAULT true,
    permiso_reportes boolean DEFAULT true,
    permiso_configuracion boolean DEFAULT false,
    permiso_escritura_registros boolean DEFAULT true NOT NULL,
    permiso_escritura_configuracion boolean DEFAULT false NOT NULL,
    pin character varying(255) DEFAULT '$2b$12$R9h/cIPz0gi.URNNX3kh2OPST9/PgBkqquzi.Ss7KIUgO2t0jWMUW'::character varying NOT NULL
);

CREATE SEQUENCE public.usuarios_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.usuarios_id_seq OWNED BY public.usuarios.id;

ALTER TABLE ONLY public.articulos ALTER COLUMN id SET DEFAULT nextval('public.articulos_id_seq'::regclass);

ALTER TABLE ONLY public.articulos_pedido ALTER COLUMN id SET DEFAULT nextval('public.articulos_pedido_id_seq'::regclass);

ALTER TABLE ONLY public.categorias_articulo ALTER COLUMN id SET DEFAULT nextval('public.categorias_articulo_id_seq'::regclass);

ALTER TABLE ONLY public.gasto_detalles ALTER COLUMN id SET DEFAULT nextval('public.gasto_detalles_id_seq'::regclass);

ALTER TABLE ONLY public.gastos ALTER COLUMN id SET DEFAULT nextval('public.gastos_id_seq'::regclass);

ALTER TABLE ONLY public.nomina_detalles ALTER COLUMN id SET DEFAULT nextval('public.nomina_detalles_id_seq'::regclass);

ALTER TABLE ONLY public.pedidos ALTER COLUMN id SET DEFAULT nextval('public.pedidos_id_seq'::regclass);

ALTER TABLE ONLY public.platillos ALTER COLUMN id SET DEFAULT nextval('public.platillos_id_seq'::regclass);

ALTER TABLE ONLY public.proveedores ALTER COLUMN id SET DEFAULT nextval('public.proveedores_id_seq'::regclass);

ALTER TABLE ONLY public.registros_asistencia ALTER COLUMN id SET DEFAULT nextval('public.registros_asistencia_id_seq'::regclass);

ALTER TABLE ONLY public.sucursales ALTER COLUMN id SET DEFAULT nextval('public.sucursales_id_seq'::regclass);

ALTER TABLE ONLY public.turno_denominaciones ALTER COLUMN id SET DEFAULT nextval('public.turno_denominaciones_id_seq'::regclass);

ALTER TABLE ONLY public.turnos ALTER COLUMN id SET DEFAULT nextval('public.turnos_id_seq'::regclass);

ALTER TABLE ONLY public.usuarios ALTER COLUMN id SET DEFAULT nextval('public.usuarios_id_seq'::regclass);


ALTER TABLE ONLY public.articulos_pedido
    ADD CONSTRAINT articulos_pedido_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.articulos
    ADD CONSTRAINT articulos_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.categorias_articulo
    ADD CONSTRAINT categorias_articulo_nombre_key UNIQUE (nombre);

ALTER TABLE ONLY public.categorias_articulo
    ADD CONSTRAINT categorias_articulo_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.gasto_detalles
    ADD CONSTRAINT gasto_detalles_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.gastos
    ADD CONSTRAINT gastos_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.nomina_detalles
    ADD CONSTRAINT nomina_detalles_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.pedidos
    ADD CONSTRAINT pedidos_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.platillos
    ADD CONSTRAINT platillos_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.proveedores
    ADD CONSTRAINT proveedores_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.registros_asistencia
    ADD CONSTRAINT registros_asistencia_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.sucursales
    ADD CONSTRAINT sucursales_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.turno_denominaciones
    ADD CONSTRAINT turno_denominaciones_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.turnos
    ADD CONSTRAINT turnos_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.pedidos
    ADD CONSTRAINT uq_numero_display_sucursal_fecha UNIQUE (numero_display, sucursal_id, fecha_creacion);

ALTER TABLE ONLY public.turno_denominaciones
    ADD CONSTRAINT uq_turno_tipo_denominacion UNIQUE (turno_id, tipo, denominacion);

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_pkey PRIMARY KEY (id);

CREATE INDEX idx_articulos_pedido_estado_item ON public.articulos_pedido USING btree (estado_item);

CREATE UNIQUE INDEX idx_turno_activo_sucursal ON public.turnos USING btree (sucursal_id) WHERE ((estado)::text = 'abierto'::text);

CREATE INDEX ix_articulos_id ON public.articulos USING btree (id);

CREATE INDEX ix_articulos_pedido_client_request_id ON public.articulos_pedido USING btree (client_request_id);

CREATE INDEX ix_articulos_pedido_id ON public.articulos_pedido USING btree (id);

CREATE INDEX ix_categorias_articulo_id ON public.categorias_articulo USING btree (id);

CREATE INDEX ix_gasto_detalles_id ON public.gasto_detalles USING btree (id);

CREATE INDEX ix_gastos_id ON public.gastos USING btree (id);

CREATE INDEX ix_nomina_detalles_gasto_id ON public.nomina_detalles USING btree (gasto_id);

CREATE INDEX ix_nomina_detalles_id ON public.nomina_detalles USING btree (id);

CREATE INDEX ix_nomina_detalles_usuario_id ON public.nomina_detalles USING btree (usuario_id);

CREATE INDEX ix_pedidos_id ON public.pedidos USING btree (id);

CREATE INDEX ix_pedidos_parent_pedido_id ON public.pedidos USING btree (parent_pedido_id);

CREATE INDEX ix_pedidos_turno_id ON public.pedidos USING btree (turno_id);

CREATE INDEX ix_platillos_id ON public.platillos USING btree (id);

CREATE INDEX ix_proveedores_id ON public.proveedores USING btree (id);

CREATE INDEX ix_registros_asistencia_id ON public.registros_asistencia USING btree (id);

CREATE INDEX ix_registros_asistencia_usuario_id ON public.registros_asistencia USING btree (usuario_id);

CREATE INDEX ix_sucursales_id ON public.sucursales USING btree (id);

CREATE INDEX ix_turno_denominaciones_id ON public.turno_denominaciones USING btree (id);

CREATE INDEX ix_turnos_id ON public.turnos USING btree (id);

CREATE INDEX ix_usuarios_id ON public.usuarios USING btree (id);

CREATE UNIQUE INDEX uq_pedidos_client_request_id ON public.pedidos USING btree (client_request_id) WHERE (client_request_id IS NOT NULL);

ALTER TABLE ONLY public.articulos
    ADD CONSTRAINT articulos_categoria_id_fkey FOREIGN KEY (categoria_id) REFERENCES public.categorias_articulo(id);

ALTER TABLE ONLY public.articulos_pedido
    ADD CONSTRAINT articulos_pedido_pedido_id_fkey FOREIGN KEY (pedido_id) REFERENCES public.pedidos(id);

ALTER TABLE ONLY public.articulos_pedido
    ADD CONSTRAINT articulos_pedido_platillo_id_fkey FOREIGN KEY (platillo_id) REFERENCES public.platillos(id);

ALTER TABLE ONLY public.pedidos
    ADD CONSTRAINT fk_pedidos_parent_pedido_id FOREIGN KEY (parent_pedido_id) REFERENCES public.pedidos(id);

ALTER TABLE ONLY public.gasto_detalles
    ADD CONSTRAINT gasto_detalles_articulo_id_fkey FOREIGN KEY (articulo_id) REFERENCES public.articulos(id);

ALTER TABLE ONLY public.gasto_detalles
    ADD CONSTRAINT gasto_detalles_gasto_id_fkey FOREIGN KEY (gasto_id) REFERENCES public.gastos(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.gastos
    ADD CONSTRAINT gastos_proveedor_id_fkey FOREIGN KEY (proveedor_id) REFERENCES public.proveedores(id);

ALTER TABLE ONLY public.gastos
    ADD CONSTRAINT gastos_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);

ALTER TABLE ONLY public.gastos
    ADD CONSTRAINT gastos_turno_id_fkey FOREIGN KEY (turno_id) REFERENCES public.turnos(id);

ALTER TABLE ONLY public.nomina_detalles
    ADD CONSTRAINT nomina_detalles_gasto_id_fkey FOREIGN KEY (gasto_id) REFERENCES public.gastos(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.nomina_detalles
    ADD CONSTRAINT nomina_detalles_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id);

ALTER TABLE ONLY public.pedidos
    ADD CONSTRAINT pedidos_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);

ALTER TABLE ONLY public.pedidos
    ADD CONSTRAINT pedidos_turno_id_fkey FOREIGN KEY (turno_id) REFERENCES public.turnos(id);

ALTER TABLE ONLY public.pedidos
    ADD CONSTRAINT pedidos_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id);

ALTER TABLE ONLY public.proveedores
    ADD CONSTRAINT proveedores_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);

ALTER TABLE ONLY public.registros_asistencia
    ADD CONSTRAINT registros_asistencia_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id);

ALTER TABLE ONLY public.turno_denominaciones
    ADD CONSTRAINT turno_denominaciones_turno_id_fkey FOREIGN KEY (turno_id) REFERENCES public.turnos(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.turnos
    ADD CONSTRAINT turnos_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);

ALTER TABLE ONLY public.turnos
    ADD CONSTRAINT turnos_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id);

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_sucursal_id_fkey FOREIGN KEY (sucursal_id) REFERENCES public.sucursales(id);


"""


def upgrade() -> None:
    op.execute(BASELINE_DDL)


def downgrade() -> None:
    op.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")

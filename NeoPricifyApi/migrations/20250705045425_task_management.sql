create table if not exists public.tasks
(
	id serial
		constraint tasks_pkey
			primary key,
	task_name varchar(100) not null
		constraint tasks_task_name_key
			unique,
	task_type varchar(50) not null,
	description text,
	is_enabled boolean default true not null,
	configuration jsonb default '{}'::jsonb not null,
	created_at timestamp with time zone default now() not null,
	updated_at timestamp with time zone default now() not null
);

create index if not exists idx_tasks_enabled
	on public.tasks (is_enabled, task_type)
	where (is_enabled = true);

create index if not exists idx_tasks_config_gin
	on public.tasks using gin (configuration);

create table if not exists public.task_executions
(
	id bigserial
		constraint task_executions_pkey
			primary key,
	task_id integer not null
		constraint task_executions_task_id_fkey
			references public.tasks
				on delete cascade,
	trigger_type trigger_type not null,
	status execution_status default 'pending'::execution_status not null,
	started_at timestamp with time zone,
	completed_at timestamp with time zone,
	duration_seconds integer,
	items_total integer,
	items_processed integer default 0,
	items_successful integer default 0,
	items_failed integer default 0,
	processing_range_start bigint,
	processing_range_end bigint,
	last_processed_id bigint,
	error_message text,
	retry_count integer default 0,
	execution_context jsonb default '{}'::jsonb,
	performance_metrics jsonb default '{}'::jsonb,
	created_at timestamp with time zone default now() not null,
	updated_at timestamp with time zone default now() not null
);

create index if not exists idx_task_executions_status_started
	on public.task_executions (status asc, started_at desc);

create index if not exists idx_task_executions_task_performance
	on public.task_executions (task_id asc, completed_at desc, duration_seconds asc);

create index if not exists idx_task_executions_metrics_gin
	on public.task_executions using gin (performance_metrics);

create index if not exists idx_task_executions_task_id_status
	on public.task_executions (task_id, status);

create table if not exists public.task_checkpoints
(
	id bigserial
		constraint task_checkpoints_pkey
			primary key,
	execution_id bigint not null
		constraint task_checkpoints_execution_id_fkey
			references public.task_executions
				on delete cascade,
	checkpoint_name varchar(100) not null,
	checkpoint_type varchar(50) not null,
	processed_up_to_id bigint,
	processed_count integer default 0,
	total_count integer,
	completion_percentage numeric(5,2),
	checkpoint_data jsonb default '{}'::jsonb not null,
	created_at timestamp with time zone default now() not null,
	constraint task_checkpoints_execution_id_checkpoint_name_key
		unique (execution_id, checkpoint_name)
);

create index if not exists idx_task_checkpoints_execution_id
	on public.task_checkpoints (execution_id);


CREATE TABLE organization (
	id INTEGER NOT NULL, 
	cortico_id INTEGER, 
	name VARCHAR NOT NULL, 
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_organization_cortico_id ON organization (cortico_id);
CREATE TABLE conversation (
	id INTEGER NOT NULL, 
	cortico_id INTEGER, 
	forum_id INTEGER, 
	project_id INTEGER, 
	conversation_guide_id INTEGER, 
	title VARCHAR NOT NULL, 
	audio_url VARCHAR, 
	duration_seconds FLOAT, 
	language VARCHAR, 
	is_open BOOLEAN NOT NULL, 
	facilitator_participant_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(forum_id) REFERENCES forum (id), 
	FOREIGN KEY(project_id) REFERENCES project (id), 
	FOREIGN KEY(conversation_guide_id) REFERENCES conversationguide (id), 
	FOREIGN KEY(facilitator_participant_id) REFERENCES participant (id)
);
CREATE UNIQUE INDEX ix_conversation_cortico_id ON conversation (cortico_id);
CREATE TABLE participant (
	id INTEGER NOT NULL, 
	conversation_id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	is_facilitator BOOLEAN NOT NULL, 
	is_registered_user BOOLEAN NOT NULL, 
	cortico_user_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(conversation_id) REFERENCES conversation (id)
);
CREATE INDEX ix_participant_cortico_user_id ON participant (cortico_user_id);
CREATE TABLE project (
	id INTEGER NOT NULL, 
	cortico_id INTEGER, 
	organization_id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	description VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organization (id)
);
CREATE UNIQUE INDEX ix_project_cortico_id ON project (cortico_id);
CREATE TABLE community (
	id INTEGER NOT NULL, 
	cortico_id INTEGER, 
	organization_id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	description VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organization (id)
);
CREATE UNIQUE INDEX ix_community_cortico_id ON community (cortico_id);
CREATE TABLE snippet (
	id INTEGER NOT NULL, 
	cortico_id INTEGER, 
	conversation_id INTEGER NOT NULL, 
	participant_id INTEGER, 
	order_index INTEGER NOT NULL, 
	start_offset FLOAT NOT NULL, 
	end_offset FLOAT NOT NULL, 
	text VARCHAR NOT NULL, 
	words VARCHAR, 
	is_facilitator_prompt BOOLEAN NOT NULL, 
	is_mechanical BOOLEAN NOT NULL, ai_score REAL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(conversation_id) REFERENCES conversation (id), 
	FOREIGN KEY(participant_id) REFERENCES participant (id)
);
CREATE UNIQUE INDEX ix_snippet_cortico_id ON snippet (cortico_id);
CREATE TABLE highlight (
	id INTEGER NOT NULL, 
	cortico_id INTEGER, 
	conversation_id INTEGER NOT NULL, 
	start_offset FLOAT NOT NULL, 
	end_offset FLOAT NOT NULL, 
	source VARCHAR(5) NOT NULL, 
	created_by VARCHAR, 
	ai_score FLOAT, 
	ai_reasoning VARCHAR, 
	created_at DATETIME NOT NULL, text VARCHAR NOT NULL DEFAULT '', guide_question_id INTEGER REFERENCES guidequestion(id), review_status TEXT NOT NULL DEFAULT 'accepted', updated_by TEXT, updated_at TEXT, original_start_offset REAL, original_end_offset REAL, original_text TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(conversation_id) REFERENCES conversation (id)
);
CREATE UNIQUE INDEX ix_highlight_cortico_id ON highlight (cortico_id);
CREATE TABLE codebook (
	id INTEGER NOT NULL, 
	cortico_id INTEGER, 
	organization_id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organization (id)
);
CREATE UNIQUE INDEX ix_codebook_cortico_id ON codebook (cortico_id);
CREATE TABLE forum (
	id INTEGER NOT NULL, 
	cortico_id INTEGER, 
	community_id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	is_public BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(community_id) REFERENCES community (id)
);
CREATE UNIQUE INDEX ix_forum_cortico_id ON forum (cortico_id);
CREATE TABLE conversationguide (
	id INTEGER NOT NULL, 
	cortico_id INTEGER, 
	project_id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	version INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES project (id)
);
CREATE UNIQUE INDEX ix_conversationguide_cortico_id ON conversationguide (cortico_id);
CREATE TABLE code (
	id INTEGER NOT NULL, 
	cortico_id INTEGER, 
	codebook_id INTEGER NOT NULL, 
	parent_code_id INTEGER, 
	name VARCHAR NOT NULL, 
	definition VARCHAR, 
	code_type VARCHAR(11) NOT NULL, 
	status VARCHAR(10) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(codebook_id) REFERENCES codebook (id), 
	FOREIGN KEY(parent_code_id) REFERENCES code (id)
);
CREATE UNIQUE INDEX ix_code_cortico_id ON code (cortico_id);
CREATE TABLE guidesection (
	id INTEGER NOT NULL, 
	conversation_guide_id INTEGER NOT NULL, 
	title VARCHAR NOT NULL, 
	order_index INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(conversation_guide_id) REFERENCES conversationguide (id)
);
CREATE TABLE highlightshare (
	id INTEGER NOT NULL, 
	cortico_id INTEGER, 
	highlight_id INTEGER NOT NULL, 
	forum_id INTEGER NOT NULL, 
	status VARCHAR(8) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(highlight_id) REFERENCES highlight (id), 
	FOREIGN KEY(forum_id) REFERENCES forum (id)
);
CREATE UNIQUE INDEX ix_highlightshare_cortico_id ON highlightshare (cortico_id);
CREATE TABLE guidequestion (
	id INTEGER NOT NULL, 
	guide_section_id INTEGER NOT NULL, 
	text VARCHAR NOT NULL, 
	shorthand_code VARCHAR, 
	order_index INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(guide_section_id) REFERENCES guidesection (id)
);
CREATE TABLE coding (
	id INTEGER NOT NULL, 
	cortico_id INTEGER, 
	code_id INTEGER NOT NULL, 
	highlight_share_id INTEGER NOT NULL, 
	is_ai_generated BOOLEAN NOT NULL, 
	created_by VARCHAR, 
	ai_reasoning VARCHAR, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(code_id) REFERENCES code (id), 
	FOREIGN KEY(highlight_share_id) REFERENCES highlightshare (id)
);
CREATE UNIQUE INDEX ix_coding_cortico_id ON coding (cortico_id);
CREATE TABLE importsnapshot (
	id INTEGER NOT NULL, 
	organization_id INTEGER NOT NULL, 
	source_environment VARCHAR NOT NULL, 
	selection_memo VARCHAR, 
	validation_status VARCHAR NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organization (id)
);
CREATE TABLE importsnapshotconversation (
	id INTEGER NOT NULL, 
	import_snapshot_id INTEGER NOT NULL, 
	conversation_id INTEGER NOT NULL, 
	cortico_conversation_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(import_snapshot_id) REFERENCES importsnapshot (id), 
	FOREIGN KEY(conversation_id) REFERENCES conversation (id)
);
CREATE INDEX ix_importsnapshotconversation_import_snapshot_id ON importsnapshotconversation (import_snapshot_id);
CREATE INDEX ix_importsnapshotconversation_conversation_id ON importsnapshotconversation (conversation_id);
CREATE TABLE sensemakingsession (
	id INTEGER NOT NULL, 
	import_snapshot_id INTEGER NOT NULL, 
	sensemaker_id VARCHAR NOT NULL, 
	sensemaker_name VARCHAR NOT NULL, 
	inquiry VARCHAR, 
	created_at DATETIME NOT NULL, 
	closed_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(import_snapshot_id) REFERENCES importsnapshot (id)
);
CREATE INDEX ix_sensemakingsession_import_snapshot_id ON sensemakingsession (import_snapshot_id);
CREATE TABLE sensemakingevent (
	id INTEGER NOT NULL, 
	sensemaking_session_id INTEGER NOT NULL, 
	actor_kind VARCHAR NOT NULL, 
	actor_id VARCHAR, 
	action VARCHAR NOT NULL, 
	target_type VARCHAR NOT NULL, 
	target_id VARCHAR, 
	before_json VARCHAR, 
	after_json VARCHAR, 
	rationale VARCHAR, 
	evidence_json VARCHAR, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(sensemaking_session_id) REFERENCES sensemakingsession (id)
);
CREATE INDEX ix_sensemakingevent_action ON sensemakingevent (action);
CREATE INDEX ix_sensemakingevent_sensemaking_session_id ON sensemakingevent (sensemaking_session_id);
CREATE INDEX ix_sensemakingevent_target_id ON sensemakingevent (target_id);
CREATE INDEX ix_sensemakingevent_target_type ON sensemakingevent (target_type);
CREATE TABLE solohighlight (
	id INTEGER NOT NULL, 
	sensemaking_session_id INTEGER NOT NULL, 
	conversation_id INTEGER NOT NULL, 
	source_highlight_id INTEGER, 
	source VARCHAR(5) NOT NULL, 
	start_offset FLOAT NOT NULL, 
	end_offset FLOAT NOT NULL, 
	text VARCHAR NOT NULL, 
	disposition VARCHAR(8) NOT NULL, 
	reactions_json VARCHAR, 
	memo VARCHAR, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(sensemaking_session_id) REFERENCES sensemakingsession (id), 
	FOREIGN KEY(conversation_id) REFERENCES conversation (id), 
	FOREIGN KEY(source_highlight_id) REFERENCES highlight (id)
);
CREATE INDEX ix_solohighlight_sensemaking_session_id ON solohighlight (sensemaking_session_id);
CREATE INDEX ix_solohighlight_conversation_id ON solohighlight (conversation_id);
CREATE TABLE soloopencode (
	id INTEGER NOT NULL, 
	sensemaking_session_id INTEGER NOT NULL, 
	solo_highlight_id INTEGER NOT NULL, 
	text VARCHAR NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(sensemaking_session_id) REFERENCES sensemakingsession (id), 
	FOREIGN KEY(solo_highlight_id) REFERENCES solohighlight (id)
);
CREATE INDEX ix_soloopencode_solo_highlight_id ON soloopencode (solo_highlight_id);
CREATE INDEX ix_soloopencode_sensemaking_session_id ON soloopencode (sensemaking_session_id);
CREATE TABLE solocodebookversion (
	id INTEGER NOT NULL, 
	sensemaking_session_id INTEGER NOT NULL, 
	version_number INTEGER, 
	note VARCHAR, 
	committed_at DATETIME, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(sensemaking_session_id) REFERENCES sensemakingsession (id)
);
CREATE INDEX ix_solocodebookversion_sensemaking_session_id ON solocodebookversion (sensemaking_session_id);
CREATE TABLE solocode (
	id INTEGER NOT NULL, 
	codebook_version_id INTEGER NOT NULL, 
	parent_id INTEGER, 
	name VARCHAR NOT NULL, 
	definition VARCHAR, 
	example_highlight_ids_json VARCHAR, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(codebook_version_id) REFERENCES solocodebookversion (id), 
	FOREIGN KEY(parent_id) REFERENCES solocode (id)
);
CREATE INDEX ix_solocode_codebook_version_id ON solocode (codebook_version_id);
CREATE TABLE solotaggingrun (
	id INTEGER NOT NULL, 
	sensemaking_session_id INTEGER NOT NULL, 
	codebook_version_id INTEGER NOT NULL, 
	previous_run_id INTEGER, 
	status VARCHAR(8) NOT NULL, 
	model VARCHAR, 
	error VARCHAR, 
	log VARCHAR, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(sensemaking_session_id) REFERENCES sensemakingsession (id), 
	FOREIGN KEY(codebook_version_id) REFERENCES solocodebookversion (id), 
	FOREIGN KEY(previous_run_id) REFERENCES solotaggingrun (id)
);
CREATE INDEX ix_solotaggingrun_sensemaking_session_id ON solotaggingrun (sensemaking_session_id);
CREATE TABLE solotagsuggestion (
	id INTEGER NOT NULL, 
	tagging_run_id INTEGER NOT NULL, 
	solo_highlight_id INTEGER NOT NULL, 
	solo_code_id INTEGER NOT NULL, 
	score FLOAT, 
	seeded BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tagging_run_id) REFERENCES solotaggingrun (id), 
	FOREIGN KEY(solo_highlight_id) REFERENCES solohighlight (id), 
	FOREIGN KEY(solo_code_id) REFERENCES solocode (id)
);
CREATE INDEX ix_solotagsuggestion_tagging_run_id ON solotagsuggestion (tagging_run_id);
CREATE INDEX ix_solotagsuggestion_solo_code_id ON solotagsuggestion (solo_code_id);
CREATE INDEX ix_solotagsuggestion_solo_highlight_id ON solotagsuggestion (solo_highlight_id);
CREATE TABLE solotagreview (
	id INTEGER NOT NULL, 
	tagging_run_id INTEGER NOT NULL, 
	solo_highlight_id INTEGER NOT NULL, 
	solo_code_id INTEGER NOT NULL, 
	disposition VARCHAR(9) NOT NULL, 
	rationale VARCHAR, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tagging_run_id) REFERENCES solotaggingrun (id), 
	FOREIGN KEY(solo_highlight_id) REFERENCES solohighlight (id), 
	FOREIGN KEY(solo_code_id) REFERENCES solocode (id)
);
CREATE INDEX ix_solotagreview_tagging_run_id ON solotagreview (tagging_run_id);
CREATE INDEX ix_solotagreview_solo_code_id ON solotagreview (solo_code_id);
CREATE INDEX ix_solotagreview_solo_highlight_id ON solotagreview (solo_highlight_id);
CREATE TABLE solosessionnote (
	id INTEGER NOT NULL, 
	sensemaking_session_id INTEGER NOT NULL, 
	kind VARCHAR NOT NULL, 
	text VARCHAR NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(sensemaking_session_id) REFERENCES sensemakingsession (id)
);
CREATE INDEX ix_solosessionnote_sensemaking_session_id ON solosessionnote (sensemaking_session_id);
CREATE INDEX ix_solosessionnote_kind ON solosessionnote (kind);
CREATE TABLE solotaggingruncodesnapshot (
	id INTEGER NOT NULL, 
	tagging_run_id INTEGER NOT NULL, 
	solo_code_id INTEGER NOT NULL, 
	definition_snapshot VARCHAR, 
	example_highlight_ids_snapshot VARCHAR, code_name VARCHAR NOT NULL DEFAULT '', 
	PRIMARY KEY (id), 
	FOREIGN KEY(tagging_run_id) REFERENCES solotaggingrun (id), 
	FOREIGN KEY(solo_code_id) REFERENCES solocode (id)
);
CREATE INDEX ix_solotaggingruncodesnapshot_tagging_run_id ON solotaggingruncodesnapshot (tagging_run_id);
CREATE INDEX ix_solotaggingruncodesnapshot_solo_code_id ON solotaggingruncodesnapshot (solo_code_id);
CREATE TABLE solotaggingrunhighlightsnapshot (
	id INTEGER NOT NULL, 
	tagging_run_id INTEGER NOT NULL, 
	solo_highlight_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tagging_run_id) REFERENCES solotaggingrun (id), 
	FOREIGN KEY(solo_highlight_id) REFERENCES solohighlight (id)
);
CREATE INDEX ix_solotaggingrunhighlightsnapshot_solo_highlight_id ON solotaggingrunhighlightsnapshot (solo_highlight_id);
CREATE INDEX ix_solotaggingrunhighlightsnapshot_tagging_run_id ON solotaggingrunhighlightsnapshot (tagging_run_id);
CREATE TABLE topictaggingwatermark (
	id INTEGER NOT NULL, 
	organization_id INTEGER NOT NULL, 
	method VARCHAR NOT NULL, 
	last_highlight_id INTEGER NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organization (id)
);
CREATE INDEX ix_topictaggingwatermark_organization_id ON topictaggingwatermark (organization_id);
CREATE INDEX ix_topictaggingwatermark_method ON topictaggingwatermark (method);
CREATE TABLE highlightprocessingwatermark (
	id INTEGER NOT NULL, 
	organization_id INTEGER NOT NULL, 
	stage VARCHAR NOT NULL, 
	last_highlight_id INTEGER NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organization (id)
);
CREATE INDEX ix_highlightprocessingwatermark_stage ON highlightprocessingwatermark (stage);
CREATE INDEX ix_highlightprocessingwatermark_organization_id ON highlightprocessingwatermark (organization_id);
CREATE INDEX ix_solotaggingruncodesnapshot_code_name ON solotaggingruncodesnapshot (code_name);
CREATE TABLE topicmapentry (
	id INTEGER NOT NULL, 
	organization_id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	definition VARCHAR NOT NULL, 
	supporting_highlight_ids_json VARCHAR NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organization (id)
);
CREATE INDEX ix_topicmapentry_name ON topicmapentry (name);
CREATE INDEX ix_topicmapentry_organization_id ON topicmapentry (organization_id);

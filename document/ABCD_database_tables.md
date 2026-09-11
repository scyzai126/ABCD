# ABCD database tables and schema
## annotated_celltype table
-	annotated_celltype_id (primary key) 
-	annotated_celltype_name
-	annotated_celltype_ontology
## vj_allele table
-	vj_allele_id (primary key) 
-	vj_allele_name
-	organism
## study table
-	study_id (primary key)
-	study_name
-	title
-	summary
-	publication_pubmed_id
-	bioproject_accession
-	geo_accession
-	sra_accession
-	study_location_igserver
-	airrflow_version
-	airflow_refgenome
-	scrnaseq_version
-	scrnaseq_refgenome
-	scintegrator_version
## study_summary table
-	study_id (primary key) (foreign key)
-	count_bcrs
-	count_igh_igk_pair
-	count_igh_igl_pair
-	count_igm
-	count_igd
-	count_iga
-	count_igg
-	count_ige
-	clonesize_mean
-	clonesize_median
-	clonesize_p05 
-	clonesize_p25
-	clonesize_p75
-	clonesize_p95
-	largest_clonesize
## study_chain_summary table
-	study_id (composite primary key) (foreign key)
-	chain (composite primary key)
-	count_chain
-	mutfreq_mean
-	mutfreq_median
-	mutfreq_p05
-	mutfreq_p25
-	mutfreq_p75
-	mutfreq_p95
-	cdr3_mean
-	cdr3_median
-	cdr3_p05
-	cdr3_p25
-	cdr3_p75
-	cdr3_p95
## study_annotated_celltype table
-	study_id (composite primary key) (foreign key)
-	annotated_celltype_id (composite primary key) (foreign key)
-	count_bcrs
-	count_igm
-	count_igd
-	count_iga
-	count_igg
-	count_ige
## study_chain_annotated_celltype_summary table
-	study_id (composite primary key) (foreign key)
-	chain (composite primary key)
-	annotated_celltype_id (composite primary key) (foreign key)
-	count_chain
-	mutfreq_mean
-	mutfreq_median
-	mutfreq_p05
-	mutfreq_p25
-	mutfreq_p75
-	mutfreq_p95
-	cdr3_mean
-	cdr3_median
-	cdr3_p05
-	cdr3_p25
-	cdr3_p75
-	cdr3_p95
## study_vj_allele table
-	study_id (composite primary key) (foreign key)
-	vj_allele_id (composite primary key) (foreign key)
-	count_vj_allele
## study_vj_allele_annotated_celltype table
-	study_id (composite primary key) (foreign key)
-	vj_allele_id (composite primary key) (foreign key)
-	annotated_celltype_id (composite primary key) (foreign key)
-	count_vj_allele

## subject table
-	subject_id (primary key)
-	study_id (foreign key)
-	subject_name
-	organism
-	strain
-	biological_sex
-	age
-	age_unit
-	age_event
-	age_event_specify_(if_other)
-	ethnicity
-	race
-	exposure_process_reported
-	exposure_material_reported
-	disease_reported
-	disease_stage
## subject_summary table
-	subject_id (primary key) (foreign key)
-	count_bcrs
-	count_igh_igk_pair
-	count_igh_igl_pair
-	count_igm
-	count_igd
-	count_iga
-	count_igg
-	count_ige
## subject_chain_summary table
-	subject_id (composite primary key) (foreign key)
-	chain (composite primary key)
-	count_chain
-	mutfreq_mean
-	mutfreq_median
-	mutfreq_p05
-	mutfreq_p25
-	mutfreq_p75
-	mutfreq_p95
-	cdr3_mean
-	cdr3_median
-	cdr3_p05
-	cdr3_p25
-	cdr3_p75
-	cdr3_p95
## subject_annotated_celltype table
-	subject_id (composite primary key) (foreign key)
-	annotated_celltype_id (composite primary key) (foreign key)
-	count_bcrs
-	count_igm
-	count_igd
-	count_iga
-	count_igg
-	count_ige
## subject_chain_annotated_celltype_summary table
-	subject_id (composite primary key) (foreign key)
-	chain (composite primary key)
-	annotated_celltype_id (composite primary key) (foreign key)
-	count_chain
-	mutfreq_mean
-	mutfreq_median
-	mutfreq_p05
-	mutfreq_p25
-	mutfreq_p75
-	mutfreq_p95
-	cdr3_mean
-	cdr3_median
-	cdr3_p05
-	cdr3_p25
-	cdr3_p75
-	cdr3_p95
## subject_vj_allele table
-	subject_id (composite primary key) (foreign key)
-	vj_allele_id (composite primary key) (foreign key)
-	count_vj_allele
## subject_vj_allele_annotated_celltype table
-	subject_id (composite primary key) (foreign key)
-	vj_allele_id (composite primary key) (foreign key)
-	annotated_celltype_id (composite primary key) (foreign key)
-	count_vj_allele


## sample table
-	sample_id (primary key)
-	subject_id (foreign key) 
-	sample_name
-	batch
-	tissue
-	cell_type
-	treatment
-	molecule
-	description
-	time_collected
-	time_collected_unit
-	time_t0_event
## sample_summary table
-	sample_id (primary key) (foreign key)
-	count_bcrs
-	count_igh_igk_pair
-	count_igh_igl_pair
-	count_igm
-	count_igd
-	count_iga
-	count_igg
-	count_ige
## sample_chain_summary table
-	sample_id (composite primary key) (foreign key)
-	chain (composite primary key)
-	count_chain
-	mutfreq_mean
-	mutfreq_median
-	mutfreq_p05
-	mutfreq_p25
-	mutfreq_p75
-	mutfreq_p95
-	cdr3_mean
-	cdr3_median
-	cdr3_p05
-	cdr3_p25
-	cdr3_p75
-	cdr3_p95
## sample_annotated_celltype table
-	sample_id (composite primary key) (foreign key)
-	annotated_celltype_id (composite primary key) (foreign key)
-	count_bcrs
-	count_igm
-	count_igd
-	count_iga
-	count_igg
-	count_ige
## sample_chain_annotated_celltype_summary table
-	sample_id (composite primary key) (foreign key)
-	chain (composite primary key)
-	annotated_celltype_id (composite primary key) (foreign key)
-	count_chain
-	mutfreq_mean
-	mutfreq_median
-	mutfreq_p05
-	mutfreq_p25
-	mutfreq_p75
-	mutfreq_p95
-	cdr3_mean
-	cdr3_median
-	cdr3_p05
-	cdr3_p25
-	cdr3_p75
-	cdr3_p95
## sample_vj_allele table
-	sample_id (composite primary key) (foreign key)
-	vj_allele_id (composite primary key) (foreign key)
-	count_vj_allele
## sample_vj_allele_annotated_celltype table
-	sample_id (composite primary key) (foreign key)
-	vj_allele_id (composite primary key) (foreign key)
-	annotated_celltype_id (composite primary key) (foreign key)
-	count_vj_allele


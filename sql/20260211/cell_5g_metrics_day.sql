/*
 Navicat Premium Dump SQL

 Source Server         : dell
 Source Server Type    : PostgreSQL
 Source Server Version : 180001 (180001)
 Source Host           : 188.15.68.62:54326
 Source Catalog        : data_wg
 Source Schema         : public

 Target Server Type    : PostgreSQL
 Target Server Version : 180001 (180001)
 File Encoding         : 65001

 Date: 11/02/2026 17:26:46
*/


-- ----------------------------
-- Table structure for cell_5g_metrics_day
-- ----------------------------
DROP TABLE IF EXISTS "public"."cell_5g_metrics_day";
CREATE TABLE "public"."cell_5g_metrics_day" (
  "id" int4 NOT NULL DEFAULT nextval('cell_5g_metrics_id_seq'::regclass),
  "start_time" timestamp(6),
  "userlabel" text COLLATE "pg_catalog"."default",
  "Ncgi" text COLLATE "pg_catalog"."default",
  "RRC_SuccConnEstab" float8,
  "RRC_AttConnEstab" float8,
  "NGSIG_ConnEstabSucc" float8,
  "NGSIG_ConnEstabAtt" float8,
  "Flow_NbrSuccEstab" float8,
  "Flow_NbrAttEstab" float8,
  "HO_SuccOutIntraFreq" float8,
  "HO_SuccOutInterFreq" float8,
  "HO_AttOutExecIntraFreq" float8,
  "HO_AttOutExecInterFreq" float8,
  "Flow_NbrMeanEstab_5QI1" float8,
  "Flow_NbrMeanEstab_5QI2" float8,
  "RRU_PuschPrbAssn" float8,
  "RRU_PuschPrbTot" float8,
  "RRU_PdschPrbTot" float8,
  "RRU_PdschPrbAssn" float8,
  "RRU_PdcchCceUtil" float8,
  "RRU_PdcchCceAvail" float8,
  "RLC_UpOctUl" float8,
  "RLC_UpOctDl" float8,
  "RRC_ConnMean" float8,
  "RRC_SAnNsaConnUserMean" float8,
  "RRC_ConnMax" float8,
  "interference" float8,
  "created_at" timestamp(6) DEFAULT now(),
  "vonr_traffic_erl" float8,
  "Flow_NbrAttEstab_ViNR" float8,
  "Flow_NbrAttEstab_VoNR" float8,
  "Flow_NbrAttEstab_5QI_1" float8,
  "CONTEXT_AttRelgNB" float8,
  "CONTEXT_AttRelgNB_Normal" float8,
  "CONTEXT_SuccInitalSetup" float8,
  "CONTEXT_NbrLeft" float8,
  "HO_SuccExecInc" float8,
  "RRC_SuccConnReestab_NonSrccell" float8,
  "HO_SuccOutInterCuNG" float8,
  "HO_SuccOutInterCuXn" float8,
  "HO_SuccOutIntraCUInterDU" float8,
  "HO_SuccOutIntraDU" float8,
  "HO_AttOutInterCuNG" float8,
  "HO_AttOutInterCuXn" float8,
  "HO_AttOutIntraCUInterDU" float8,
  "HO_AttOutCUIntraDU" float8
)
;

-- ----------------------------
-- Indexes structure for table cell_5g_metrics_day
-- ----------------------------
CREATE INDEX "idx_cell_5g_day_label_time" ON "public"."cell_5g_metrics_day" USING btree (
  "userlabel" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "start_time" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_cell_5g_day_time_range" ON "public"."cell_5g_metrics_day" USING btree (
  "start_time" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);
CREATE UNIQUE INDEX "idx_pg_5g_day_unique" ON "public"."cell_5g_metrics_day" USING btree (
  "start_time" "pg_catalog"."timestamp_ops" ASC NULLS LAST,
  "Ncgi" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE UNIQUE INDEX "idx_pg_5g_hour_unique_copy1" ON "public"."cell_5g_metrics_day" USING btree (
  "start_time" "pg_catalog"."timestamp_ops" ASC NULLS LAST,
  "Ncgi" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE UNIQUE INDEX "idx_pg_5g_unique_copy1_copy1" ON "public"."cell_5g_metrics_day" USING btree (
  "start_time" "pg_catalog"."timestamp_ops" ASC NULLS LAST,
  "Ncgi" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Uniques structure for table cell_5g_metrics_day
-- ----------------------------
ALTER TABLE "public"."cell_5g_metrics_day" ADD CONSTRAINT "cell_5g_metrics_hour_copy1_start_time_Ncgi_key" UNIQUE ("start_time", "Ncgi");

-- ----------------------------
-- Primary Key structure for table cell_5g_metrics_day
-- ----------------------------
ALTER TABLE "public"."cell_5g_metrics_day" ADD CONSTRAINT "cell_5g_metrics_hour_copy1_pkey" PRIMARY KEY ("id");

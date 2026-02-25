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

 Date: 31/12/2025 16:36:11
*/


-- ----------------------------
-- Table structure for cell_5g_metrics
-- ----------------------------
DROP TABLE IF EXISTS "public"."cell_5g_metrics";
CREATE TABLE "public"."cell_5g_metrics" (
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
  "vonr_traffic_erl" float8
)
;

-- ----------------------------
-- Indexes structure for table cell_5g_metrics
-- ----------------------------
CREATE INDEX "idx_metrics_5g_cgi" ON "public"."cell_5g_metrics" USING btree (
  "Ncgi" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_metrics_5g_time" ON "public"."cell_5g_metrics" USING btree (
  "start_time" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_metrics_5g_time_cgi" ON "public"."cell_5g_metrics" USING btree (
  "start_time" "pg_catalog"."timestamp_ops" DESC NULLS FIRST,
  "Ncgi" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE UNIQUE INDEX "idx_pg_5g_unique" ON "public"."cell_5g_metrics" USING btree (
  "start_time" "pg_catalog"."timestamp_ops" ASC NULLS LAST,
  "Ncgi" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Uniques structure for table cell_5g_metrics
-- ----------------------------
ALTER TABLE "public"."cell_5g_metrics" ADD CONSTRAINT "uq_cell_5g" UNIQUE ("start_time", "Ncgi");

-- ----------------------------
-- Primary Key structure for table cell_5g_metrics
-- ----------------------------
ALTER TABLE "public"."cell_5g_metrics" ADD CONSTRAINT "cell_5g_metrics_pkey" PRIMARY KEY ("id");

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

 Date: 11/02/2026 17:25:29
*/


-- ----------------------------
-- Table structure for cell_4g_metrics
-- ----------------------------
DROP TABLE IF EXISTS "public"."cell_4g_metrics";
CREATE TABLE "public"."cell_4g_metrics" (
  "id" int4 NOT NULL DEFAULT nextval('cell_4g_metrics_id_seq'::regclass),
  "start_time" timestamp(6),
  "omcr" text COLLATE "pg_catalog"."default",
  "cell_id" text COLLATE "pg_catalog"."default",
  "cgi" text COLLATE "pg_catalog"."default",
  "cellname" text COLLATE "pg_catalog"."default",
  "enbid" int4,
  "lcrid" int4,
  "RRU_CellUnavailableTime" float8,
  "PDCP_UpOctUl" float8,
  "PDCP_UpOctDl" float8,
  "RRC_AttConnEstab" float8,
  "RRC_SuccConnEstab" float8,
  "ERAB_NbrAttEstab" float8,
  "ERAB_NbrSuccEstab" float8,
  "ERAB_NbrMeanEstab_1" float8,
  "HO_SuccOutInterEnbS1" float8,
  "HO_SuccOutInterEnbX2" float8,
  "HO_SuccOutIntraEnb" float8,
  "HO_AttOutInterEnbS1" float8,
  "HO_AttOutInterEnbX2" float8,
  "HO_AttOutIntraEnb" float8,
  "RRU_PuschPrbAssn" float8,
  "RRU_PuschPrbTot" float8,
  "RRU_PdschPrbAssn" float8,
  "RRU_PdschPrbTot" float8,
  "RRU_PdcchCceUtil" float8,
  "RRU_PdcchCceAvail" float8,
  "RRC_ConnMax" float8,
  "total_traffic_gb" float8,
  "rrc_success_rate" float8,
  "erab_success_rate" float8,
  "wireless_connect_rate" float8,
  "wireless_drop_rate" float8,
  "erab_drop_rate" float8,
  "handover_success_rate" float8,
  "volte_traffic_erl" float8,
  "qci1_erab_success_rate" float8,
  "cells_over_200_users" int4,
  "cells_over_400_users" int4,
  "cells_over_50pct_ul_prb" int4,
  "cells_over_50pct_dl_prb" int4,
  "qci1_drop_rate" float8,
  "cqi_low_ratio" float8,
  "volte_ul_packet_loss_rate" float8,
  "volte_dl_packet_loss_rate" float8,
  "dl_prb_utilization" float8,
  "ul_prb_utilization" float8,
  "cce_utilization" float8,
  "ul_speed_mbps" float8,
  "dl_speed_mbps" float8,
  "uplink_traffic_gb" float8,
  "downlink_traffic_gb" float8,
  "interference" float8,
  "created_at" timestamp(6) DEFAULT now(),
  "ERAB_HoFail" float8,
  "ERAB_NbrReqRelEnb_Normal" float8,
  "ERAB_NbrReqRelEnb" float8,
  "CONTEXT_NbrLeft" float8,
  "ERAB_NbrHoInc" float8
)
;

-- ----------------------------
-- Indexes structure for table cell_4g_metrics
-- ----------------------------
CREATE INDEX "idx_cell_4g_metrics_omcr_time" ON "public"."cell_4g_metrics" USING btree (
  "omcr" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "start_time" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_cell_4g_metrics_time_range" ON "public"."cell_4g_metrics" USING btree (
  "start_time" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_metrics_4g_cell_id" ON "public"."cell_4g_metrics" USING btree (
  "cell_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_metrics_4g_cellname" ON "public"."cell_4g_metrics" USING btree (
  "cellname" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_metrics_4g_cgi" ON "public"."cell_4g_metrics" USING btree (
  "cgi" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_metrics_4g_time" ON "public"."cell_4g_metrics" USING btree (
  "start_time" "pg_catalog"."timestamp_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_metrics_4g_time_cgi" ON "public"."cell_4g_metrics" USING btree (
  "start_time" "pg_catalog"."timestamp_ops" DESC NULLS FIRST,
  "cgi" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE UNIQUE INDEX "idx_pg_4g_unique" ON "public"."cell_4g_metrics" USING btree (
  "start_time" "pg_catalog"."timestamp_ops" ASC NULLS LAST,
  "cgi" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "time_cel" ON "public"."cell_4g_metrics" USING btree (
  "start_time" "pg_catalog"."timestamp_ops" ASC NULLS LAST,
  "cellname" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Uniques structure for table cell_4g_metrics
-- ----------------------------
ALTER TABLE "public"."cell_4g_metrics" ADD CONSTRAINT "uq_cell_4g" UNIQUE ("start_time", "cell_id");

-- ----------------------------
-- Primary Key structure for table cell_4g_metrics
-- ----------------------------
ALTER TABLE "public"."cell_4g_metrics" ADD CONSTRAINT "cell_4g_metrics_pkey" PRIMARY KEY ("id");

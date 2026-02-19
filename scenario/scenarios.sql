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

 Date: 06/02/2026 15:01:55
*/


-- ----------------------------
-- Table structure for scenarios
-- ----------------------------
DROP TABLE IF EXISTS "public"."scenarios";
CREATE TABLE "public"."scenarios" (
  "id" int4 NOT NULL DEFAULT nextval('scenarios_id_seq'::regclass),
  "scenario_name" text COLLATE "pg_catalog"."default" NOT NULL,
  "description" text COLLATE "pg_catalog"."default",
  "created_at" timestamp(6) DEFAULT now(),
  "updated_at" timestamp(6) DEFAULT now()
)
;

-- ----------------------------
-- Records of scenarios
-- ----------------------------
INSERT INTO "public"."scenarios" VALUES (11, '移动大楼', '', '2026-01-05 11:18:39.838871', '2026-01-05 11:18:39.838871');
INSERT INTO "public"."scenarios" VALUES (21, '高铁主覆盖小区', '', '2026-01-27 11:39:12.693634', '2026-01-27 11:39:12.693634');
INSERT INTO "public"."scenarios" VALUES (22, '广湛高铁', '', '2026-01-27 11:43:51.301438', '2026-01-27 11:43:51.301438');
INSERT INTO "public"."scenarios" VALUES (23, '深湛高铁', '', '2026-01-27 11:44:10.348711', '2026-01-27 11:44:10.348711');
INSERT INTO "public"."scenarios" VALUES (31, '燕山胡活动', '', '2026-01-28 11:28:51.713142', '2026-01-28 11:28:51.713142');
INSERT INTO "public"."scenarios" VALUES (32, '1月23号活动', '', '2026-01-30 10:44:05.067271', '2026-01-30 10:44:05.067271');
INSERT INTO "public"."scenarios" VALUES (33, '鸳鸯湖活动-0130', '', '2026-01-30 11:46:15.783279', '2026-01-30 11:46:15.783279');
INSERT INTO "public"."scenarios" VALUES (34, '罗阳高速', '', '2026-02-03 10:19:34.856723', '2026-02-03 10:19:34.856723');
INSERT INTO "public"."scenarios" VALUES (35, '汕湛高速', '', '2026-02-03 10:22:27.971491', '2026-02-03 10:22:27.971491');
INSERT INTO "public"."scenarios" VALUES (36, '沈海高速', '', '2026-02-03 10:26:26.456378', '2026-02-03 10:26:26.456378');
INSERT INTO "public"."scenarios" VALUES (37, '西部沿海高速', '', '2026-02-03 10:28:57.60661', '2026-02-03 10:28:57.60661');
INSERT INTO "public"."scenarios" VALUES (38, '信阳高速', '', '2026-02-03 10:31:08.422472', '2026-02-03 10:31:08.422472');
INSERT INTO "public"."scenarios" VALUES (39, '中阳高速', '', '2026-02-03 10:33:22.472831', '2026-02-03 10:33:22.472831');
INSERT INTO "public"."scenarios" VALUES (40, '2月东湖活动', '', '2026-02-03 11:06:52.544645', '2026-02-03 11:06:52.544645');
INSERT INTO "public"."scenarios" VALUES (41, '高速主覆盖小区', '', '2026-02-05 09:35:57.529598', '2026-02-05 09:35:57.529598');
INSERT INTO "public"."scenarios" VALUES (42, '文旅大联欢活动覆盖小区', '', '2026-02-05 10:11:50.983119', '2026-02-05 10:11:50.983119');

-- ----------------------------
-- Uniques structure for table scenarios
-- ----------------------------
ALTER TABLE "public"."scenarios" ADD CONSTRAINT "scenarios_scenario_name_key" UNIQUE ("scenario_name");

-- ----------------------------
-- Primary Key structure for table scenarios
-- ----------------------------
ALTER TABLE "public"."scenarios" ADD CONSTRAINT "scenarios_pkey" PRIMARY KEY ("id");

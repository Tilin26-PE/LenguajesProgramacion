import Dependencies._

ThisBuild / scalaVersion     := "2.13.16"
ThisBuild / version          := "0.1.0-SNAPSHOT"
ThisBuild / organization     := "com.example"
ThisBuild / organizationName := "example"

lazy val root = (project in file("."))
  .settings(
    name := "pedidocore",
    libraryDependencies += munit % Test,

    // JAR autocontenido (incluye scala-library) para no depender de
    // caches locales de Coursier/Ivy al correr en un servidor (Render, etc).
    assembly / mainClass := Some("pedidocore.Main"),
    assembly / assemblyJarName := "pedidocore-assembly.jar",
    assembly / assemblyMergeStrategy := {
      case PathList("META-INF", xs @ _*) => MergeStrategy.discard
      case _ => MergeStrategy.first
    }
  )

// See https://www.scala-sbt.org/1.x/docs/Using-Sonatype.html for instructions on how to publish to Sonatype.

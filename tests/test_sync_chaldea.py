from server.sync_chaldea import parse_dart_enum, parse_effect_schema


def test_parse_dart_enum_extracts_values_labels_and_extra(tmp_path):
    dart_file = tmp_path / "common.dart"
    dart_file.write_text(
        """
enum SvtClass {
  saber(1, '剣', 1),
  archer(2, '弓', 2),
  unknown(-1);

  final int value;
}
""",
        encoding="utf-8",
    )

    assert parse_dart_enum(dart_file, "SvtClass") == [
        {"name": "saber", "value": 1, "label": "剣", "baseClassId": 1},
        {"name": "archer", "value": 2, "label": "弓", "baseClassId": 2},
        {"name": "unknown", "value": -1},
    ]


def test_parse_effect_schema_extracts_buff_func_and_constructor_forms(tmp_path):
    dart_file = tmp_path / "effect.dart"
    dart_file.write_text(
        """
class SkillEffect {
  static List<SkillEffect> kAttack = [upAtk, gainNp, upCommand];
  static List<SkillEffect> kDefence = [invincible];
  static List<SkillEffect> kDebuffRelated = [];
  static List<SkillEffect> kOthers = [];

  static SkillEffect upAtk = SkillEffect._buff('upAtk', BuffType.upAtk);
  static SkillEffect gainNp = SkillEffect._func('gainNp', FuncType.gainNp);
  static SkillEffect upCommand = SkillEffect(
    'upArts',
    funcTypes: [FuncType.addState],
    buffTypes: [BuffType.upCommandall, BuffType.upCommandnp],
  );
  static SkillEffect invincible = SkillEffect._buff('invincible', BuffType.invincible);
}
""",
        encoding="utf-8",
    )

    effects = {effect["name"]: effect for effect in parse_effect_schema(dart_file)}

    assert effects["upAtk"]["category"] == "attack"
    assert effects["upAtk"]["buffTypes"] == ["upAtk"]
    assert effects["gainNp"]["funcTypes"] == ["gainNp"]
    assert effects["upArts"]["funcTypes"] == ["addState"]
    assert effects["upArts"]["buffTypes"] == ["upCommandall", "upCommandnp"]
    assert effects["invincible"]["category"] == "defence"
    assert effects["invincible"]["aliases_zh"] == ["无敌"]

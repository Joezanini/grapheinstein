import 'package:flutter/material.dart';
import 'dart:async';
export 'simple.dart';
part 'part_file.dart';

mixin MyMixin {
  void mixinMethod() {}
  void anotherMixinMethod() {}
}

extension MyExtension on String {
  void extensionMethod() {}
}

enum Status {
  active,
  inactive,
  pending
}

typedef Callback = void Function();

class GenericClass<T> {
  T? value;
  
  void setValue(T newValue) {
    value = newValue;
  }
  
  T? getValue() => value;
}

void callSomeFunction() {
  topLevelFunction();
  SimpleClass().instanceMethod();
}
